"""WebSocket-tier load test for live quiz sessions.

Locust's HttpUser (locustfile.py) can't reproduce the scenario that
matters most for the live quiz feature: hundreds of students already
connected to the same room, all receiving a question reveal and all
answering within the same second. This script drives that scenario
directly with asyncio + websockets and reports the same style of
p50/p95/p99 latency summary Locust prints for the REST tier, so the two
are easy to compare side by side.

What it measures, per run:
  - reveal_latency_ms: from the instructor sending question.advance to
    each individual student's connection receiving question.revealed.
    This is the "how fast does the locked waiting screen unlock" claim.
  - chart_latency_ms: from a student sending answer.submit (fired for
    every student at effectively the same instant, via
    asyncio.gather - the "everyone answers at once" spike) to that same
    student receiving the chart.update broadcast reflecting it. This is
    the "how fast does the bar chart update" claim.

Usage (against a seeded, running backend - see README.md):
    python manage.py seed_demo --students 200   # once, from backend/
    python loadtests/ws_load_test.py --host http://localhost:8000 --students 200

Requires: pip install -r loadtests/requirements.txt
(websockets + requests; both also already used elsewhere in this repo's
manual testing, not new tooling introduced just for this script).
"""
import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import requests
import websockets

DEMO_PASSWORD = 'password123'
INSTRUCTOR_USERNAME = 'demo_instructor'
LOAD_TEST_COURSE_TITLE = 'Introduction to Python'
LOAD_TEST_QUIZ_TITLE = 'Load Test Quiz'
CHART_WAIT_TIMEOUT_SECONDS = 15


def http_login(host, username, password):
    response = requests.post(
        f'{host}/api/auth/login/', json={'username': username, 'password': password}, timeout=10
    )
    response.raise_for_status()
    return response.json()['access']


def resolve_quiz(host, instructor_token, student_token):
    # quiz_list works for the instructor (or anyone), but /take/ is
    # IsStudent + enrollment-gated (see quizzes/views.py::quiz_take) -
    # resolving the question id needs a real seeded student's token,
    # not the instructor's.
    instructor_headers = {'Authorization': f'Bearer {instructor_token}'}
    courses = requests.get(f'{host}/api/courses/', headers=instructor_headers, timeout=10).json()
    course = next((c for c in courses if c['title'] == LOAD_TEST_COURSE_TITLE), None)
    if course is None:
        raise SystemExit(
            f'Could not find seeded course "{LOAD_TEST_COURSE_TITLE}". '
            'Run `python manage.py seed_demo --students N` first.'
        )

    quizzes = requests.get(
        f'{host}/api/courses/{course["id"]}/quizzes/', headers=instructor_headers, timeout=10
    ).json()
    quiz = next((q for q in quizzes if q['title'] == LOAD_TEST_QUIZ_TITLE), None)
    if quiz is None:
        raise SystemExit(f'Could not find seeded quiz "{LOAD_TEST_QUIZ_TITLE}" on "{LOAD_TEST_COURSE_TITLE}".')

    student_headers = {'Authorization': f'Bearer {student_token}'}
    take = requests.get(f'{host}/api/quizzes/{quiz["id"]}/take/', headers=student_headers, timeout=10).json()
    question_id = take['questions'][0]['id']
    return quiz['id'], question_id


def percentile(values, pct):
    if not values:
        return float('nan')
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (pct / 100)
    floor_index = int(k)
    ceil_index = min(floor_index + 1, len(values_sorted) - 1)
    if floor_index == ceil_index:
        return values_sorted[floor_index]
    return values_sorted[floor_index] + (values_sorted[ceil_index] - values_sorted[floor_index]) * (k - floor_index)


def summarize(name, latencies_ms):
    if not latencies_ms:
        print(f'{name}: no samples collected (all connections may have failed - see errors above)')
        return
    print(
        f'{name}: n={len(latencies_ms)} '
        f'mean={statistics.mean(latencies_ms):.1f}ms '
        f'p50={percentile(latencies_ms, 50):.1f}ms '
        f'p95={percentile(latencies_ms, 95):.1f}ms '
        f'p99={percentile(latencies_ms, 99):.1f}ms '
        f'max={max(latencies_ms):.1f}ms'
    )


async def connect_student(ws_host, room_code, student_index):
    username = f'loadtest_student_{student_index:04d}'
    try:
        token = await asyncio.to_thread(http_login, ws_host_to_http(ws_host), username, DEMO_PASSWORD)
    except Exception as exc:
        return None, f'{username}: login failed ({exc})'

    uri = f'{ws_host}/ws/live/{room_code}/'
    try:
        ws = await websockets.connect(uri, subprotocols=[token], open_timeout=10)
        await ws.recv()  # session.state
        return ws, None
    except Exception as exc:
        return None, f'{username}: connect failed ({exc})'


async def wait_for_reveal(ws, t0):
    while True:
        message = json.loads(await ws.recv())
        if message.get('type') == 'question.revealed':
            return (time.monotonic() - t0) * 1000


async def submit_and_wait_for_chart(ws, question_id, t_submit_start):
    await ws.send(json.dumps({'type': 'answer.submit', 'question_id': question_id, 'answer': ['b']}))

    deadline = time.monotonic() + CHART_WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        except asyncio.TimeoutError:
            break
        if message.get('type') == 'chart.update':
            return (time.monotonic() - t_submit_start) * 1000
    return None


def ws_host_to_http(ws_host):
    return ws_host.replace('ws://', 'http://').replace('wss://', 'https://')


def append_json_result(output_path, record):
    """Appends one JSON-lines record per run, so a ladder of runs at
    different --students values can be aggregated afterward by
    generate_graphs.py without needing a database or a running server
    to re-derive them from.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(record) + '\n')


async def run(http_host, ws_host, num_students):
    print(f'Setting up: {num_students} students against {http_host} ({ws_host} for WebSocket)...')

    instructor_token = http_login(http_host, INSTRUCTOR_USERNAME, DEMO_PASSWORD)
    probe_student_token = http_login(http_host, 'loadtest_student_0000', DEMO_PASSWORD)
    quiz_id, question_id = resolve_quiz(http_host, instructor_token, probe_student_token)

    session_resp = requests.post(
        f'{http_host}/api/quizzes/{quiz_id}/sessions/',
        headers={'Authorization': f'Bearer {instructor_token}'},
        timeout=10,
    )
    session_resp.raise_for_status()
    room_code = session_resp.json()['room_code']

    requests.post(
        f'{http_host}/api/sessions/{room_code}/start/',
        headers={'Authorization': f'Bearer {instructor_token}'},
        timeout=10,
    ).raise_for_status()
    print(f'Live session started: room_code={room_code}, quiz_id={quiz_id}, question_id={question_id}')

    host_ws = await websockets.connect(f'{ws_host}/ws/live/{room_code}/', subprotocols=[instructor_token])
    await host_ws.recv()  # session.state

    print(f'Connecting {num_students} students...')
    results = await asyncio.gather(*(connect_student(ws_host, room_code, i) for i in range(num_students)))
    students = [ws for ws, _err in results if ws is not None]
    errors = [err for _ws, err in results if err is not None]
    for err in errors[:10]:
        print(f'  WARNING: {err}')
    if len(errors) > 10:
        print(f'  ... and {len(errors) - 10} more connection errors')
    print(f'{len(students)}/{num_students} students connected successfully.')

    if not students:
        raise SystemExit('No students connected - aborting.')

    # Phase 1: reveal latency. All students are already blocked in
    # recv() past session.state, so sending advance and racing gather()
    # against every student's next message is a true "how long until
    # this specific connection sees the reveal" measurement.
    t0 = time.monotonic()
    await host_ws.send(json.dumps({'type': 'question.advance'}))
    reveal_latencies = await asyncio.gather(*(wait_for_reveal(ws, t0) for ws in students))

    # Phase 2: the "everyone answers at once" spike. asyncio.gather
    # schedules every submit_and_wait_for_chart call before yielding
    # control back to the event loop for the first await inside any of
    # them, so all students' answer.submit sends happen essentially
    # back-to-back rather than serialized one at a time.
    t_submit_start = time.monotonic()
    chart_latencies_raw = await asyncio.gather(
        *(submit_and_wait_for_chart(ws, question_id, t_submit_start) for ws in students)
    )
    chart_latencies = [latency for latency in chart_latencies_raw if latency is not None]
    missing_chart_updates = len(chart_latencies_raw) - len(chart_latencies)

    await host_ws.send(json.dumps({'type': 'session.end'}))
    await asyncio.gather(*(ws.close() for ws in students), return_exceptions=True)
    await host_ws.close()

    print()
    print(f'=== Results (room {room_code}, {len(students)} connected students) ===')
    summarize('reveal_latency_ms  (question.advance -> question.revealed received)', reveal_latencies)
    summarize('chart_latency_ms   (answer.submit -> chart.update received)', chart_latencies)
    if missing_chart_updates:
        print(f'  WARNING: {missing_chart_updates} student(s) never received a chart.update within '
              f'{CHART_WAIT_TIMEOUT_SECONDS}s.')

    return {
        'num_students': len(students),
        'reveal_latency_ms': {
            'p50': percentile(reveal_latencies, 50),
            'p95': percentile(reveal_latencies, 95),
            'p99': percentile(reveal_latencies, 99),
        },
        'chart_latency_ms': {
            'p50': percentile(chart_latencies, 50),
            'p95': percentile(chart_latencies, 95),
            'p99': percentile(chart_latencies, 99),
        },
        'missing_chart_updates': missing_chart_updates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', required=True, help='HTTP base URL, e.g. http://localhost:8000')
    parser.add_argument('--ws-host', default=None, help='WebSocket base URL (default: derived from --host)')
    parser.add_argument('--students', type=int, default=100, help='Number of concurrent students to simulate')
    parser.add_argument(
        '--output-json',
        default=None,
        help='Append this run\'s summary as one JSON line to this file (for generate_graphs.py to plot a ladder).',
    )
    args = parser.parse_args()

    ws_host = args.ws_host or args.host.replace('http://', 'ws://').replace('https://', 'wss://')
    summary = asyncio.run(run(args.host, ws_host, args.students))

    if args.output_json:
        append_json_result(args.output_json, summary)
        print(f'\nAppended summary to {args.output_json}')


if __name__ == '__main__':
    main()
