import datetime
from unittest.mock import patch

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from .models import Course, Chapter, Enrollment
from .views import CATALOG_CACHE_KEY
from schedule.models import Term


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


class CourseChatOpenFieldTests(APITestCase):
    """Covers CourseSerializer.chat_open, the REST-visible signal the
    chat frontend (M15) uses to disable the composer proactively, and
    which messaging/consumers.py's write-lock mirrors server-side."""

    def setUp(self):
        cache.clear()
        self.instructor = User.objects.create_user(
            username='chatopen_instructor', password='password123', role='instructor'
        )
        self.client.force_authenticate(user=self.instructor)

    def tearDown(self):
        cache.clear()

    def test_course_with_no_term_is_always_open(self):
        course = Course.objects.create(title='No Term Course', instructor=self.instructor, is_published=True)

        response = self.client.get(f'/api/courses/{course.id}/')

        self.assertTrue(response.data['chat_open'])

    def test_course_with_future_term_end_date_is_open(self):
        term = Term.objects.create(
            name='Future Term',
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
        )
        course = Course.objects.create(
            title='Future Term Course', instructor=self.instructor, is_published=True, term=term
        )

        response = self.client.get(f'/api/courses/{course.id}/')

        self.assertTrue(response.data['chat_open'])

    def test_course_with_past_term_end_date_is_closed(self):
        term = Term.objects.create(
            name='Past Term',
            start_date=datetime.date.today() - datetime.timedelta(days=60),
            end_date=datetime.date.today() - datetime.timedelta(days=1),
        )
        course = Course.objects.create(
            title='Past Term Course', instructor=self.instructor, is_published=True, term=term
        )

        response = self.client.get(f'/api/courses/{course.id}/')

        self.assertFalse(response.data['chat_open'])
