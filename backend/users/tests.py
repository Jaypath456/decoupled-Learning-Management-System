from django.conf import settings
from django.test import TestCase

from lms_project.celery import app as celery_app
from lms_project.tasks import heartbeat


class CeleryScaffoldTests(TestCase):
    """lms_project isn't a Django "app" (no models/views of its own),
    so these infrastructure checks live here rather than needing a
    dedicated test-only app. Covers the M12 Celery scaffold: no real
    scheduled jobs exist yet beyond this heartbeat, which exists to
    prove the worker/beat wiring is correct before anything depends on
    it (the course-chat tenure-reset purge job, in a later milestone).
    """

    def test_heartbeat_task_runs_and_returns_ok(self):
        # Task functions decorated with @app.task remain directly
        # callable without a running worker/broker - this exercises the
        # actual task body, not Celery's dispatch machinery.
        self.assertEqual(heartbeat(), 'ok')

    def test_heartbeat_is_registered_with_the_celery_app(self):
        self.assertIn('lms_project.tasks.heartbeat', celery_app.tasks)

    def test_beat_schedule_includes_the_heartbeat(self):
        self.assertIn('heartbeat-every-minute', settings.CELERY_BEAT_SCHEDULE)
        entry = settings.CELERY_BEAT_SCHEDULE['heartbeat-every-minute']
        self.assertEqual(entry['task'], 'lms_project.tasks.heartbeat')

    def test_celery_broker_and_result_backend_point_at_redis_url(self):
        self.assertEqual(settings.CELERY_BROKER_URL, settings.REDIS_URL)
        self.assertEqual(settings.CELERY_RESULT_BACKEND, settings.REDIS_URL)
