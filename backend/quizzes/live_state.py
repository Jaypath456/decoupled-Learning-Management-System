"""Ephemeral live-session state in Redis, mirroring LiveSession's DB
status on every REST transition (M16) and every WebSocket-driven
per-question transition (the live quiz consumer, consumers.py).

Redis holds the "hot" state the consumer needs to check on every message
without hitting Postgres each time; the LiveSession row remains the
durable source of truth and is exactly what gets read back if Redis is
flushed or restarted mid-session - nothing here is ever the only copy of
anything that matters. The one exception is the live chart counters
below, which are genuinely ephemeral (visualization only) and are never
read back from anywhere else - see consumers.py for how the same
information is reconstructed from Postgres (Submission.answers) at
question-close time for the "chart counts equal Postgres submission
counts" guarantee.
"""
import logging

from django.core.cache import cache

from lms_project.safe_cache import safe_delete, safe_get, safe_set

logger = logging.getLogger(__name__)

# Generous relative to how long a single live quiz session realistically
# runs - this is a safety-net expiry, not a session-length assumption.
SESSION_STATE_TTL_SECONDS = 60 * 60 * 6
CHART_TTL_SECONDS = 60 * 60 * 6


def _state_key(room_code):
    return f'live_session_state:{room_code}'


def _chart_key(room_code, question_id):
    return f'live_chart:{room_code}:{question_id}'


def set_session_state(session):
    safe_set(
        _state_key(session.room_code),
        {
            'quiz_id': session.quiz_id,
            'host_id': session.host_id,
            'status': session.status,
            'current_question_index': session.current_question_index,
        },
        timeout=SESSION_STATE_TTL_SECONDS,
    )


def get_session_state(room_code):
    return safe_get(_state_key(room_code))


def clear_session_state(room_code):
    safe_delete(_state_key(room_code))


def _redis_client():
    # django-redis exposes the raw redis-py client for operations (hash
    # field increments) that Django's generic cache API doesn't cover.
    # This ties chart tracking specifically to the django-redis backend,
    # which is an acceptable coupling here since it's already the only
    # supported CACHES backend for this project (see settings.py).
    return cache.client.get_client()


def increment_chart_bucket(room_code, question_id, bucket):
    """Bumps one bucket (an option id for choice questions, or
    'correct'/'incorrect' for short_answer - see consumers.py) in a
    question's live chart by one. Best-effort: a chart update that fails
    to land never blocks or invalidates the answer it came from - the
    chart is a visualization, not a correctness record (that's
    Postgres's job, via the Submission row consumers.py writes
    separately in the same request).
    """
    try:
        _redis_client().hincrby(_chart_key(room_code, question_id), bucket, 1)
        cache.expire(_chart_key(room_code, question_id), CHART_TTL_SECONDS)
    except Exception:
        logger.warning(
            'Chart increment failed for room=%s question=%s bucket=%s',
            room_code, question_id, bucket, exc_info=True,
        )


def get_chart_counts(room_code, question_id):
    try:
        raw = _redis_client().hgetall(_chart_key(room_code, question_id))
        return {
            (k.decode() if isinstance(k, bytes) else k): int(v)
            for k, v in raw.items()
        }
    except Exception:
        logger.warning(
            'Chart read failed for room=%s question=%s', room_code, question_id, exc_info=True,
        )
        return {}


def clear_chart(room_code, question_id):
    safe_delete(_chart_key(room_code, question_id))
