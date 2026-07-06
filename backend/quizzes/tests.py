from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course
from users.models import User

from .models import Question, Quiz


def choice_body(options, correct_option_ids, prompt_text='What is 2+2?'):
    return {
        'prompt': [{'type': 'paragraph', 'children': [{'text': prompt_text}]}],
        'options': options,
        'correct_option_ids': correct_option_ids,
    }


def short_answer_body(correct_answer, prompt_text='Name the capital of France.'):
    return {
        'prompt': [{'type': 'paragraph', 'children': [{'text': prompt_text}]}],
        'correct_answer': correct_answer,
    }


class QuizOwnershipTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='quiz_owner', password='password123', role='instructor'
        )
        self.other_instructor = User.objects.create_user(
            username='quiz_other_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='quiz_student', password='password123', role='student'
        )
        self.course = Course.objects.create(
            title='Quiz Course', instructor=self.owner, is_published=True
        )

    def test_owner_can_create_quiz(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/courses/{self.course.id}/quizzes/create/',
            {'title': 'Midterm', 'description': 'Covers chapters 1-3'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Midterm')
        self.assertFalse(response.data['is_published'])
        self.assertEqual(response.data['question_count'], 0)

    def test_non_owner_instructor_cannot_create_quiz(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.post(
            f'/api/courses/{self.course.id}/quizzes/create/', {'title': 'Sneaky Quiz'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Quiz.objects.filter(course=self.course).exists())

    def test_student_cannot_create_quiz(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f'/api/courses/{self.course.id}/quizzes/create/', {'title': 'Sneaky Quiz'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_and_publish_quiz(self):
        quiz = Quiz.objects.create(course=self.course, title='Draft Quiz')
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f'/api/quizzes/{quiz.id}/', {'is_published': True}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_published'])

    def test_non_owner_instructor_cannot_update_quiz(self):
        quiz = Quiz.objects.create(course=self.course, title='Draft Quiz')
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.put(
            f'/api/quizzes/{quiz.id}/', {'title': 'Hacked'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        quiz.refresh_from_db()
        self.assertEqual(quiz.title, 'Draft Quiz')

    def test_non_owner_instructor_cannot_delete_quiz(self):
        quiz = Quiz.objects.create(course=self.course, title='Draft Quiz')
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.delete(f'/api/quizzes/{quiz.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Quiz.objects.filter(id=quiz.id).exists())

    def test_owner_can_delete_quiz(self):
        quiz = Quiz.objects.create(course=self.course, title='Draft Quiz')
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f'/api/quizzes/{quiz.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=quiz.id).exists())


class QuizVisibilityTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='visibility_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='visibility_student', password='password123', role='student'
        )
        self.course = Course.objects.create(
            title='Visibility Course', instructor=self.instructor, is_published=True
        )
        self.published_quiz = Quiz.objects.create(
            course=self.course, title='Published Quiz', is_published=True
        )
        self.draft_quiz = Quiz.objects.create(
            course=self.course, title='Draft Quiz', is_published=False
        )

    def test_owner_sees_both_published_and_draft_quizzes(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get(f'/api/courses/{self.course.id}/quizzes/')

        titles = {quiz['title'] for quiz in response.data}
        self.assertEqual(titles, {'Published Quiz', 'Draft Quiz'})

    def test_student_only_sees_published_quizzes(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/courses/{self.course.id}/quizzes/')

        titles = {quiz['title'] for quiz in response.data}
        self.assertEqual(titles, {'Published Quiz'})

    def test_student_cannot_read_draft_quiz_detail(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/quizzes/{self.draft_quiz.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_read_published_quiz_detail(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/quizzes/{self.published_quiz.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Published Quiz')

    def test_owner_can_read_draft_quiz_detail(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get(f'/api/quizzes/{self.draft_quiz.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class QuestionOwnershipTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='question_owner', password='password123', role='instructor'
        )
        self.other_instructor = User.objects.create_user(
            username='question_other_instructor', password='password123', role='instructor'
        )
        self.student = User.objects.create_user(
            username='question_student', password='password123', role='student'
        )
        self.course = Course.objects.create(
            title='Question Course', instructor=self.owner, is_published=True
        )
        self.quiz = Quiz.objects.create(course=self.course, title='Quiz 1')
        self.question = Question.objects.create(
            quiz=self.quiz,
            question_type=Question.SINGLE_CHOICE,
            body=choice_body(
                [{'id': 'a', 'text': '3'}, {'id': 'b', 'text': '4'}], ['b']
            ),
        )

    def test_owner_can_create_single_choice_question(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/quizzes/{self.quiz.id}/questions/create/',
            {
                'question_type': 'single_choice',
                'body': choice_body(
                    [{'id': 'a', 'text': 'Paris'}, {'id': 'b', 'text': 'Rome'}], ['a']
                ),
                'points': 2,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['points'], 2)
        self.assertEqual(response.data['body']['correct_option_ids'], ['a'])

    def test_non_owner_instructor_cannot_create_question(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.post(
            f'/api/quizzes/{self.quiz.id}/questions/create/',
            {'question_type': 'single_choice', 'body': choice_body(
                [{'id': 'a', 'text': 'x'}], ['a']
            )},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_question(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f'/api/quizzes/{self.quiz.id}/questions/create/',
            {'question_type': 'single_choice', 'body': choice_body(
                [{'id': 'a', 'text': 'x'}], ['a']
            )},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_instructor_cannot_update_question(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.put(
            f'/api/questions/{self.question.id}/', {'points': 99}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.question.refresh_from_db()
        self.assertEqual(self.question.points, 1)

    def test_non_owner_instructor_cannot_delete_question(self):
        self.client.force_authenticate(user=self.other_instructor)

        response = self.client.delete(f'/api/questions/{self.question.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Question.objects.filter(id=self.question.id).exists())

    def test_owner_can_read_update_and_delete_question(self):
        self.client.force_authenticate(user=self.owner)

        get_response = self.client.get(f'/api/questions/{self.question.id}/')
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        put_response = self.client.put(
            f'/api/questions/{self.question.id}/', {'points': 5}, format='json'
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.assertEqual(put_response.data['points'], 5)

        delete_response = self.client.delete(f'/api/questions/{self.question.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Question.objects.filter(id=self.question.id).exists())


class QuestionBodyValidationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='validation_owner', password='password123', role='instructor'
        )
        self.course = Course.objects.create(
            title='Validation Course', instructor=self.owner, is_published=True
        )
        self.quiz = Quiz.objects.create(course=self.course, title='Quiz 1')
        self.client.force_authenticate(user=self.owner)

    def _create(self, question_type, body):
        return self.client.post(
            f'/api/quizzes/{self.quiz.id}/questions/create/',
            {'question_type': question_type, 'body': body},
            format='json',
        )

    def test_valid_multiple_choice_question(self):
        response = self._create(
            'multiple_choice',
            choice_body(
                [{'id': 'a', 'text': 'Cat'}, {'id': 'b', 'text': 'Dog'}, {'id': 'c', 'text': 'Rock'}],
                ['a', 'b'],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_valid_short_answer_question(self):
        response = self._create('short_answer', short_answer_body('Paris'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_single_choice_rejects_multiple_correct_answers(self):
        response = self._create(
            'single_choice',
            choice_body(
                [{'id': 'a', 'text': '3'}, {'id': 'b', 'text': '4'}], ['a', 'b']
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_choice_question_rejects_empty_options(self):
        response = self._create('single_choice', choice_body([], []))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_choice_question_rejects_correct_id_not_in_options(self):
        response = self._create(
            'single_choice', choice_body([{'id': 'a', 'text': '3'}], ['nonexistent'])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_answer_rejects_blank_correct_answer(self):
        response = self._create('short_answer', short_answer_body('   '))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_body_must_be_an_object(self):
        response = self._create('short_answer', 'not-an-object')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
