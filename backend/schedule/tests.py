from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course
from users.models import User

from .models import Break, Meeting, Section, Term


class TermTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='term_user', password='password123', role='student')
        Term.objects.create(name='Summer 2026', start_date='2026-06-01', end_date='2026-08-15')
        Term.objects.create(name='Fall 2026', start_date='2026-09-01', end_date='2026-12-15')

    def test_authenticated_user_can_list_terms(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/terms/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_user_cannot_list_terms(self):
        response = self.client.get('/api/terms/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SectionOwnershipTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='section_owner', password='password123', role='instructor'
        )
        self.other_instructor = User.objects.create_user(
            username='section_other_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='section_student', password='password123', role='student'
        )
        self.course = Course.objects.create(
            title='Section Course', instructor=self.owner, is_published=True
        )
        self.term = Term.objects.create(
            name='Summer 2026', start_date='2026-06-01', end_date='2026-08-15'
        )

    def _section_payload(self, **overrides):
        payload = {
            'term': self.term.id,
            'section_code': 'LEC 001',
            'location': 'Hoch 114',
            'capacity': 50,
            'meetings': [
                {'day_of_week': 0, 'start_time': '10:00:00', 'end_time': '11:15:00'},
                {'day_of_week': 2, 'start_time': '10:00:00', 'end_time': '11:15:00'},
            ],
        }
        payload.update(overrides)
        return payload

    def test_owner_can_create_section_with_meetings(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/', self._section_payload(), format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['meetings']), 2)
        self.assertEqual(Section.objects.count(), 1)
        self.assertEqual(Meeting.objects.count(), 2)

    def test_non_owner_instructor_cannot_create_section(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/', self._section_payload(), format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Section.objects.exists())

    def test_student_cannot_create_section(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/', self._section_payload(), format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anyone_authenticated_can_read_sections(self):
        section = Section.objects.create(course=self.course, term=self.term, section_code='LEC 001')
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/courses/{self.course.id}/sections/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], section.id)

    def test_section_list_can_filter_by_term(self):
        other_term = Term.objects.create(
            name='Fall 2026', start_date='2026-09-01', end_date='2026-12-15'
        )
        Section.objects.create(course=self.course, term=self.term, section_code='LEC 001')
        Section.objects.create(course=self.course, term=other_term, section_code='LEC 002')
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/courses/{self.course.id}/sections/?term={self.term.id}')

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['section_code'], 'LEC 001')

    def test_non_owner_instructor_cannot_update_section(self):
        section = Section.objects.create(course=self.course, term=self.term, section_code='LEC 001')
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.put(
            f'/api/sections/{section.id}/', {'section_code': 'HACKED'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        section.refresh_from_db()
        self.assertEqual(section.section_code, 'LEC 001')

    def test_owner_can_update_section_meetings(self):
        section = Section.objects.create(course=self.course, term=self.term, section_code='LEC 001')
        Meeting.objects.create(section=section, day_of_week=0, start_time='09:00:00', end_time='09:50:00')
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f'/api/sections/{section.id}/',
            {'meetings': [{'day_of_week': 3, 'start_time': '14:00:00', 'end_time': '15:15:00'}]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(section.meetings.count(), 1)
        self.assertEqual(section.meetings.first().day_of_week, 3)

    def test_non_owner_instructor_cannot_delete_section(self):
        section = Section.objects.create(course=self.course, term=self.term, section_code='LEC 001')
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.delete(f'/api/sections/{section.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Section.objects.filter(id=section.id).exists())

    def test_owner_can_delete_section(self):
        section = Section.objects.create(course=self.course, term=self.term, section_code='LEC 001')
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f'/api/sections/{section.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Section.objects.filter(id=section.id).exists())


class MeetingValidationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='meeting_owner', password='password123', role='instructor'
        )
        self.course = Course.objects.create(
            title='Meeting Course', instructor=self.owner, is_published=True
        )
        self.term = Term.objects.create(
            name='Summer 2026', start_date='2026-06-01', end_date='2026-08-15'
        )
        self.client.force_authenticate(user=self.owner)

    def test_rejects_end_time_before_start_time(self):
        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/',
            {
                'term': self.term.id,
                'meetings': [{'day_of_week': 0, 'start_time': '11:00:00', 'end_time': '10:00:00'}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_end_time_equal_to_start_time(self):
        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/',
            {
                'term': self.term.id,
                'meetings': [{'day_of_week': 0, 'start_time': '10:00:00', 'end_time': '10:00:00'}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_day_of_week(self):
        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/',
            {
                'term': self.term.id,
                'meetings': [{'day_of_week': 9, 'start_time': '10:00:00', 'end_time': '11:00:00'}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accepts_valid_meeting(self):
        response = self.client.post(
            f'/api/courses/{self.course.id}/sections/create/',
            {
                'term': self.term.id,
                'meetings': [{'day_of_week': 4, 'start_time': '09:00:00', 'end_time': '09:50:00'}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class BreakTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='break_student', password='password123', role='student'
        )
        self.other_student = User.objects.create_user(
            username='break_other_student', password='password123', role='student'
        )
        self.instructor = User.objects.create_user(
            username='break_instructor', password='password123', role='instructor'
        )

    def test_student_can_create_and_list_own_breaks(self):
        self.client.force_authenticate(user=self.student)

        create_response = self.client.post(
            '/api/breaks/',
            {'day_of_week': 0, 'start_time': '08:00:00', 'end_time': '10:00:00', 'label': 'No morning classes'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get('/api/breaks/')
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]['label'], 'No morning classes')

    def test_instructor_cannot_create_breaks(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.post(
            '/api/breaks/', {'day_of_week': 0, 'start_time': '08:00:00', 'end_time': '10:00:00'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_breaks_rejects_end_before_start(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            '/api/breaks/', {'day_of_week': 0, 'start_time': '10:00:00', 'end_time': '08:00:00'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_only_sees_own_breaks(self):
        Break.objects.create(
            student=self.other_student, day_of_week=1, start_time='09:00:00', end_time='10:00:00'
        )
        Break.objects.create(
            student=self.student, day_of_week=2, start_time='09:00:00', end_time='10:00:00'
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/breaks/')

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['day_of_week'], 2)

    def test_student_can_delete_own_break(self):
        brk = Break.objects.create(
            student=self.student, day_of_week=0, start_time='08:00:00', end_time='10:00:00'
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.delete(f'/api/breaks/{brk.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Break.objects.filter(id=brk.id).exists())

    def test_student_cannot_delete_another_students_break(self):
        brk = Break.objects.create(
            student=self.other_student, day_of_week=0, start_time='08:00:00', end_time='10:00:00'
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.delete(f'/api/breaks/{brk.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Break.objects.filter(id=brk.id).exists())


class CourseTermFieldTests(APITestCase):
    """Covers the nullable Course.term FK added alongside the schedule app."""

    def test_course_can_be_created_without_a_term(self):
        instructor = User.objects.create_user(
            username='term_field_instructor', password='password123', role='instructor'
        )
        course = Course.objects.create(title='Termless Course', instructor=instructor)
        self.assertIsNone(course.term)

    def test_course_term_survives_term_deletion_as_null(self):
        instructor = User.objects.create_user(
            username='term_field_instructor2', password='password123', role='instructor'
        )
        term = Term.objects.create(name='Winter 2026', start_date='2026-01-01', end_date='2026-03-01')
        course = Course.objects.create(title='Termed Course', instructor=instructor, term=term)

        term.delete()
        course.refresh_from_db()

        self.assertIsNone(course.term)
