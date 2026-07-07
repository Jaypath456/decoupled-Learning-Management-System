import io
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
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

    @override_settings(LOAD_TEST_DISABLE_REDIS_OPTIMIZATIONS=True)
    def test_caching_is_skipped_when_load_test_toggle_disables_it(self):
        Course.objects.create(title='Toggle Course', instructor=self.instructor, is_published=True)

        first = self.client.get('/api/courses/')
        self.assertEqual(len(first.data), 1)
        self.assertIsNone(cache.get(CATALOG_CACHE_KEY))

        # With caching disabled, a course created after the first
        # request DOES show up on the very next request (no stale
        # cached response in the way) - the opposite of
        # test_second_request_is_served_from_cache above.
        Course.objects.create(title='Also Visible', instructor=self.instructor, is_published=True)
        second = self.client.get('/api/courses/')
        self.assertEqual(len(second.data), 2)


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

    def test_students_flag_is_a_no_op_by_default(self):
        self._run_seed()

        self.assertFalse(User.objects.filter(username__startswith='loadtest_student_').exists())

    def test_students_flag_seeds_load_test_scale_data(self):
        call_command('seed_demo', students=25, stdout=io.StringIO())

        loadtest_students = User.objects.filter(username__startswith='loadtest_student_')
        self.assertEqual(loadtest_students.count(), 25)
        self.assertTrue(User.objects.filter(username='loadtest_student_0000').exists())
        self.assertTrue(User.objects.filter(username='loadtest_student_0024').exists())

        published_course = Course.objects.get(title='Introduction to Python')
        self.assertEqual(
            Enrollment.objects.filter(course=published_course, student__username__startswith='loadtest_student_').count(),
            25,
        )

        from quizzes.models import Quiz
        self.assertTrue(Quiz.objects.filter(course=published_course, title='Load Test Quiz').exists())

    def test_students_flag_is_idempotent(self):
        call_command('seed_demo', students=10, stdout=io.StringIO())
        first_count = User.objects.filter(username__startswith='loadtest_student_').count()

        call_command('seed_demo', students=10, stdout=io.StringIO())
        second_count = User.objects.filter(username__startswith='loadtest_student_').count()

        self.assertEqual(first_count, second_count)
        self.assertEqual(first_count, 10)


class EnrollmentPermissionTests(APITestCase):
    """Covers the manage_enrollment fix: role gating + published-only enroll."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username='enroll_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='enroll_student', password='password123', role='student'
        )
        self.published_course = Course.objects.create(
            title='Published Course', instructor=self.instructor, is_published=True
        )
        self.draft_course = Course.objects.create(
            title='Draft Course', instructor=self.instructor, is_published=False
        )

    def test_student_can_enroll_in_published_course(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(f'/api/courses/{self.published_course.id}/enroll/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=self.published_course).exists()
        )

    def test_student_cannot_enroll_in_unpublished_course(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(f'/api/courses/{self.draft_course.id}/enroll/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=self.draft_course).exists()
        )

    def test_instructor_cannot_enroll(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.post(f'/api/courses/{self.published_course.id}/enroll/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_repeated_enroll_is_idempotent(self):
        self.client.force_authenticate(user=self.student)

        self.client.post(f'/api/courses/{self.published_course.id}/enroll/')
        response = self.client.post(f'/api/courses/{self.published_course.id}/enroll/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, course=self.published_course).count(),
            1,
        )

    def test_student_can_unenroll(self):
        Enrollment.objects.create(student=self.student, course=self.published_course)
        self.client.force_authenticate(user=self.student)

        response = self.client.delete(f'/api/courses/{self.published_course.id}/enroll/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=self.published_course).exists()
        )

    def test_instructor_cannot_unenroll(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.delete(f'/api/courses/{self.published_course.id}/enroll/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CourseOwnershipTests(APITestCase):
    """Regression coverage for the ownership checks refactored onto
    IsCourseInstructor in course_detail/chapter_create."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='course_owner', password='password123', role='instructor'
        )
        self.other_instructor = User.objects.create_user(
            username='other_instructor', password='password123', role='instructor'
        )
        self.course = Course.objects.create(
            title='Owned Course', instructor=self.owner, is_published=True
        )

    def test_owner_can_update_course(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f'/api/courses/{self.course.id}/', {'title': 'Updated Title'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_non_owner_instructor_cannot_update_course(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.put(
            f'/api/courses/{self.course.id}/', {'title': 'Hacked Title'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Owned Course')

    def test_non_owner_instructor_cannot_delete_course(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.delete(f'/api/courses/{self.course.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())

    def test_non_owner_instructor_cannot_create_chapter(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.post(
            f'/api/courses/{self.course.id}/chapters/create/',
            {'title': 'Sneaky Chapter'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Chapter.objects.filter(course=self.course).exists())


class ChapterOwnershipTests(APITestCase):
    """Regression coverage for the ownership checks refactored onto
    IsCourseInstructor in chapter_detail."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='chapter_owner', password='password123', role='instructor'
        )
        self.other_instructor = User.objects.create_user(
            username='other_chapter_instructor', password='password123', role='instructor'
        )
        self.course = Course.objects.create(
            title='Course', instructor=self.owner, is_published=True
        )
        self.chapter = Chapter.objects.create(
            course=self.course, title='Chapter 1', visibility='private'
        )

    def test_non_owner_instructor_cannot_update_chapter(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.put(
            f'/api/chapters/{self.chapter.id}/', {'title': 'Hacked'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.title, 'Chapter 1')

    def test_non_owner_instructor_cannot_delete_chapter(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.delete(f'/api/chapters/{self.chapter.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Chapter.objects.filter(id=self.chapter.id).exists())


class StudentRosterTests(APITestCase):
    """Covers removal of the phantom phone_number field from the roster."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username='roster_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='roster_student',
            password='password123',
            email='roster_student@test.com',
            role='student',
        )
        self.course = Course.objects.create(
            title='Roster Course', instructor=self.instructor, is_published=True
        )
        Enrollment.objects.create(student=self.student, course=self.course)

    def test_roster_response_has_no_phone_field(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get(f'/api/courses/{self.course.id}/students/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn('phone', response.data[0])
        self.assertEqual(response.data[0]['email'], 'roster_student@test.com')
