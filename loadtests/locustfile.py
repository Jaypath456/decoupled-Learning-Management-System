"""Locust load-test scenarios for the LMS REST API.

Run against a seeded backend (see loadtests/README.md for the full
setup):
    python manage.py seed_demo --students 1000

Then, from the repo root:
    locust -f loadtests/locustfile.py --host http://localhost:8000

Each simulated user logs in once as one of the seeded
loadtest_student_NNNN accounts, then repeatedly exercises the exact
request sequence the frontend already makes for the same flows (see
frontend/src/pages/student/Catalog.js and CourseView.js) - this file
replays the real access pattern, it doesn't invent a synthetic one.

NUM_SEEDED_STUDENTS must match whatever --students value was used when
seeding, so logins are spread across the full seeded population instead
of hammering a handful of accounts.
"""
import random

from locust import HttpUser, between, task

NUM_SEEDED_STUDENTS = 1000
DEMO_PASSWORD = 'password123'
LOAD_TEST_COURSE_TITLE = 'Introduction to Python'
LOAD_TEST_QUIZ_TITLE = 'Load Test Quiz'


class LMSStudent(HttpUser):
    """Mirrors a real student session: log in once, then repeatedly
    browse the catalog, view+enroll in a course (the exact multi-request
    burst CourseView.js's Promise.all triple-fetch produces), and take
    the seeded load-test quiz."""

    wait_time = between(1, 3)

    def on_start(self):
        student_index = random.randint(0, NUM_SEEDED_STUDENTS - 1)
        username = f'loadtest_student_{student_index:04d}'

        response = self.client.post(
            '/api/auth/login/',
            json={'username': username, 'password': DEMO_PASSWORD},
            name='POST /api/auth/login/',
        )
        if response.status_code != 200:
            # A failed login means the account wasn't seeded - fail
            # loudly rather than silently running a user that can never
            # do anything, which would just look like "everything is
            # fast" for all the wrong reasons.
            response.failure(f'Login failed for {username}: {response.status_code} {response.text[:200]}')
            self.environment.runner.quit()
            return

        token = response.json()['access']
        self.client.headers.update({'Authorization': f'Bearer {token}'})

        self.course_id = None
        self.quiz_id = None
        self.question_id = None

    @task(3)
    def browse_catalog(self):
        self.client.get('/api/courses/', name='GET /api/courses/')

    @task(2)
    def view_course_and_enroll(self):
        course_id = self._resolve_course_id()
        if course_id is None:
            return

        # The same three-request parallel burst CourseView.js issues via
        # Promise.all on every course page load.
        self.client.get(f'/api/courses/{course_id}/', name='GET /api/courses/[id]/')
        self.client.get(f'/api/courses/{course_id}/chapters/', name='GET /api/courses/[id]/chapters/')
        self.client.get(
            f'/api/courses/{course_id}/enrollment-status/',
            name='GET /api/courses/[id]/enrollment-status/',
        )
        self.client.post(f'/api/courses/{course_id}/enroll/', name='POST /api/courses/[id]/enroll/')

    @task(1)
    def take_and_submit_quiz(self):
        quiz_id, question_id = self._resolve_quiz()
        if quiz_id is None or question_id is None:
            return

        self.client.get(f'/api/quizzes/{quiz_id}/take/', name='GET /api/quizzes/[id]/take/')
        # This is the endpoint the idempotency load-testing story (M21,
        # and the before/after Redis comparison) cares about most -
        # every simulated student submits exactly once per run, so
        # timings here reflect the real first-submission cost, not
        # duplicate-detection overhead.
        self.client.post(
            f'/api/quizzes/{quiz_id}/submit/',
            json={'answers': {str(question_id): ['b']}},
            name='POST /api/quizzes/[id]/submit/',
        )

    def _resolve_course_id(self):
        if self.course_id is not None:
            return self.course_id

        response = self.client.get('/api/courses/', name='GET /api/courses/ (resolve fixtures)')
        courses = response.json() if response.status_code == 200 else []
        matches = [c for c in courses if c['title'] == LOAD_TEST_COURSE_TITLE]
        if not matches:
            return None

        self.course_id = matches[0]['id']
        return self.course_id

    def _resolve_quiz(self):
        if self.quiz_id is not None:
            return self.quiz_id, self.question_id

        course_id = self._resolve_course_id()
        if course_id is None:
            return None, None

        response = self.client.get(
            f'/api/courses/{course_id}/quizzes/', name='GET /api/courses/[id]/quizzes/ (resolve fixtures)'
        )
        quizzes = response.json() if response.status_code == 200 else []
        matches = [q for q in quizzes if q['title'] == LOAD_TEST_QUIZ_TITLE]
        if not matches:
            return None, None
        self.quiz_id = matches[0]['id']

        take_response = self.client.get(
            f'/api/quizzes/{self.quiz_id}/take/', name='GET /api/quizzes/[id]/take/ (resolve fixtures)'
        )
        questions = take_response.json().get('questions', []) if take_response.status_code == 200 else []
        self.question_id = questions[0]['id'] if questions else None

        return self.quiz_id, self.question_id
