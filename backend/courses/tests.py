import io
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from .models import Course, Chapter, Enrollment
from .views import CATALOG_CACHE_KEY


class ChapterAccessTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            password='password123',
            role='instructor'
        )
        self.student = User.objects.create_user(
            username='student',
            password='password123',
            role='student'
        )
        self.course = Course.objects.create(
            title='Intro to LMS',
            description='A short course',
            instructor=self.instructor,
            is_published=True
        )
        self.public_chapter = Chapter.objects.create(
            course=self.course,
            title='Public chapter',
            visibility='public',
            content=[{'type': 'paragraph', 'children': [{'text': 'Hello'}]}]
        )
        self.private_chapter = Chapter.objects.create(
            course=self.course,
            title='Private chapter',
            visibility='private',
            content=[{'type': 'paragraph', 'children': [{'text': 'Secret'}]}]
        )

    def test_student_must_enroll_to_read_public_chapter(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chapters/{self.public_chapter.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enrolled_student_can_read_public_chapter(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chapters/{self.public_chapter.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.public_chapter.title)

    def test_enrolled_student_cannot_read_private_chapter(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chapters/{self.private_chapter.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_read_private_chapter(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get(f'/api/chapters/{self.private_chapter.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.private_chapter.title)


class CatalogCacheTests(APITestCase):
    """Covers Redis-backed caching of the course_list endpoint, its
    invalidation on writes, and graceful degradation if the cache
    backend is unreachable."""

    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            username='cache_student', password='password123', role='student'
        )
        self.instructor = User.objects.create_user(
            username='cache_instructor', password='password123', role='instructor'
        )
        self.client.force_authenticate(user=self.student)

    def tearDown(self):
        cache.clear()

    def test_second_request_is_served_from_cache(self):
        Course.objects.create(title='Cached Course', instructor=self.instructor, is_published=True)

        first = self.client.get('/api/courses/')
        self.assertEqual(len(first.data), 1)

        # A course created after the first request should NOT appear on
        # a second request if it's truly served from cache.
        Course.objects.create(title='Not Yet Cached', instructor=self.instructor, is_published=True)
        second = self.client.get('/api/courses/')

        self.assertEqual(len(second.data), 1)
        self.assertEqual(second.data, first.data)

    def test_cache_is_invalidated_on_course_create(self):
        self.client.force_authenticate(user=self.instructor)
        self.client.get('/api/courses/')  # warm the cache with 0 courses

        self.client.post('/api/courses/create/', {'title': 'Brand New', 'is_published': True}, format='json')

        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/courses/')
        self.assertEqual(len(response.data), 1)

    def test_cache_is_invalidated_on_publish_toggle(self):
        course = Course.objects.create(title='Draft', instructor=self.instructor, is_published=False)
        self.client.get('/api/courses/')  # warm the cache with 0 published courses

        self.client.force_authenticate(user=self.instructor)
        self.client.put(f'/api/courses/{course.id}/', {'is_published': True}, format='json')

        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/courses/')
        self.assertEqual(len(response.data), 1)

    def test_cache_is_invalidated_on_course_delete(self):
        course = Course.objects.create(title='To Delete', instructor=self.instructor, is_published=True)
        self.client.get('/api/courses/')  # warm the cache with 1 course

        self.client.force_authenticate(user=self.instructor)
        self.client.delete(f'/api/courses/{course.id}/')

        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/courses/')
        self.assertEqual(len(response.data), 0)

    def test_catalog_still_works_if_cache_get_is_unavailable(self):
        Course.objects.create(title='Resilient Course', instructor=self.instructor, is_published=True)

        with patch('django.core.cache.cache.get', side_effect=ConnectionError('redis down')):
            response = self.client.get('/api/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_catalog_still_works_if_cache_set_is_unavailable(self):
        Course.objects.create(title='Resilient Course 2', instructor=self.instructor, is_published=True)

        with patch('django.core.cache.cache.set', side_effect=ConnectionError('redis down')):
            response = self.client.get('/api/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_cache_key_used_matches_expected_constant(self):
        # Sanity check that the view is actually using the documented
        # cache key (so ops/debugging docs referencing it stay accurate).
        self.client.get('/api/courses/')
        self.assertIsNotNone(cache.get(CATALOG_CACHE_KEY))


class SeedDemoCommandTests(TestCase):
    """Covers the seed_demo management command used by the Docker Compose
    workflow (docker compose exec backend python manage.py seed_demo)."""

    def _run_seed(self):
        call_command('seed_demo', stdout=io.StringIO())

    def test_seed_creates_expected_demo_data(self):
        self._run_seed()

        self.assertTrue(User.objects.filter(username='demo_instructor', role='instructor').exists())
        self.assertTrue(User.objects.filter(username='demo_student', role='student').exists())
        self.assertTrue(Course.objects.filter(title='Introduction to Python', is_published=True).exists())
        self.assertTrue(Course.objects.filter(title='Unpublished Draft Course', is_published=False).exists())

        published_course = Course.objects.get(title='Introduction to Python')
        self.assertTrue(Chapter.objects.filter(course=published_course).exists())
        self.assertTrue(Enrollment.objects.filter(course=published_course).exists())

        # Draft courses are never seeded with enrollments.
        draft_course = Course.objects.get(title='Unpublished Draft Course')
        self.assertFalse(Enrollment.objects.filter(course=draft_course).exists())

    def test_seed_is_idempotent(self):
        self._run_seed()
        first_user_count = User.objects.count()
        first_course_count = Course.objects.count()
        first_chapter_count = Chapter.objects.count()
        first_enrollment_count = Enrollment.objects.count()

        self._run_seed()

        self.assertEqual(User.objects.count(), first_user_count)
        self.assertEqual(Course.objects.count(), first_course_count)
        self.assertEqual(Chapter.objects.count(), first_chapter_count)
        self.assertEqual(Enrollment.objects.count(), first_enrollment_count)

    def test_seeded_instructor_can_log_in_with_documented_password(self):
        self._run_seed()

        user = User.objects.get(username='demo_instructor')
        self.assertTrue(user.check_password('password123'))
