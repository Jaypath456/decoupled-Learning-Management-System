"""Ephemeral live-session state in Redis, mirroring LiveSession's DB
status on every REST transition (and, in a later milestone, every
WebSocket-driven per-question transition too).

Redis holds the "hot" state the live quiz consumer (a later milestone)
needs to check on every message without hitting Postgres each time; the
LiveSession row remains the durable source of truth and is exactly what
gets read back if Redis is flushed or restarted mid-session - nothing
here is ever the only copy of anything that matters.
"""
from lms_project.safe_cache import safe_delete, safe_get, safe_set

# Generous relative to how long a single live quiz session realistically
# runs - this is a safety-net expiry, not a session-length assumption.
SESSION_STATE_TTL_SECONDS = 60 * 60 * 6


def _state_key(room_code):
    return f'live_session_state:{room_code}'


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
