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


class CourseCatalogQueryTests(APITestCase):
    """Covers the M4 pagination + N+1 fixes for the public catalog."""

    NUM_COURSES = 50

    def setUp(self):
        self.instructor = User.objects.create_user(
            username='catalog_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='catalog_student', password='password123', role='student'
        )

        self.courses = []
        for i in range(self.NUM_COURSES):
            course = Course.objects.create(
                title=f'Course {i}', instructor=self.instructor, is_published=True
            )
            Chapter.objects.create(course=course, title='Chapter 1', visibility='public')
            self.courses.append(course)

        # Enroll the student in a handful of courses so enrolled_count > 0
        # for at least some rows.
        for course in self.courses[:5]:
            Enrollment.objects.create(student=self.student, course=course)

    def test_catalog_response_is_paginated(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], self.NUM_COURSES)
        self.assertEqual(len(response.data['results']), 12)  # default page_size
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_catalog_query_count_is_constant_regardless_of_course_count(self):
        self.client.force_authenticate(user=self.student)

        # 1 query for the annotated/select_related page of courses,
        # 1 query for the paginator's total .count(). This must not grow
        # with the number of courses (the N+1 the audit originally flagged).
        with self.assertNumQueries(2):
            response = self.client.get('/api/courses/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_catalog_counts_match_manual_counts(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/courses/')

        for item in response.data['results']:
            course = Course.objects.get(id=item['id'])
            self.assertEqual(item['chapter_count'], course.chapters.count())
            self.assertEqual(item['enrolled_count'], course.enrollments.count())

    def test_can_load_next_page(self):
        self.client.force_authenticate(user=self.student)

        first_page = self.client.get('/api/courses/')
        next_url = first_page.data['next']
        # DRF returns an absolute URL (http://testserver/api/courses/?page=2);
        # the Django test client only needs the path + querystring.
        next_path = next_url.split('testserver', 1)[-1]

        second_page = self.client.get(next_path)

        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page.data['results']), 12)
        first_ids = {c['id'] for c in first_page.data['results']}
        second_ids = {c['id'] for c in second_page.data['results']}
        self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_instructor_courses_endpoint_is_not_paginated(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get('/api/courses/mine/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), self.NUM_COURSES)

    def test_instructor_courses_counts_are_correct(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get('/api/courses/mine/')

        for item in response.data:
            course = Course.objects.get(id=item['id'])
            self.assertEqual(item['chapter_count'], course.chapters.count())
            self.assertEqual(item['enrolled_count'], course.enrollments.count())

    def test_my_courses_nested_course_counts_still_correct(self):
        # my_courses is not annotated (nested via select_related), so this
        # exercises CourseSerializer's fallback .count() path rather than
        # the annotated fast path - both must return the same numbers.
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/my-courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        for item in response.data:
            course = Course.objects.get(id=item['course']['id'])
            self.assertEqual(item['course']['chapter_count'], course.chapters.count())
            self.assertEqual(item['course']['enrolled_count'], course.enrollments.count())

    def test_course_create_response_has_zero_counts(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.post(
            '/api/courses/create/', {'title': 'Brand New Course'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['chapter_count'], 0)
        self.assertEqual(response.data['enrolled_count'], 0)

    def test_course_detail_counts_match_manual_counts(self):
        self.client.force_authenticate(user=self.student)
        course = self.courses[0]

        response = self.client.get(f'/api/courses/{course.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chapter_count'], course.chapters.count())
        self.assertEqual(response.data['enrolled_count'], course.enrollments.count())
