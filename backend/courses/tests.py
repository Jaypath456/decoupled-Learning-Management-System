from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from .models import Course, Chapter, Enrollment


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
