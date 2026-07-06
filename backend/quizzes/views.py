from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from courses.models import Course
from courses.permissions import IsCourseInstructor, IsInstructor

from .models import Question, Quiz
from .serializers import QuestionSerializer, QuizSerializer


def _is_quiz_owner(request, quiz):
    # IsCourseInstructor.has_object_permission already handles any object
    # exposing a `course` FK - a Quiz has exactly that, so this reuses the
    # existing permission class as-is (see courses/permissions.py).
    return IsCourseInstructor().has_object_permission(request, None, quiz)


def _is_question_owner(request, question):
    # Question only has a `quiz` FK, not `course` directly, so resolve one
    # hop first and then reuse the same IsCourseInstructor check against
    # the parent quiz.
    return IsCourseInstructor().has_object_permission(request, None, question.quiz)


# ─── Quiz Views ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quiz_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_owner = IsCourseInstructor().has_object_permission(request, None, course)

    if is_owner:
        quizzes = Quiz.objects.filter(course=course)
    elif course.is_published:
        quizzes = Quiz.objects.filter(course=course, is_published=True)
    else:
        return Response({'error': 'This course is not available'}, status=status.HTTP_403_FORBIDDEN)

    serializer = QuizSerializer(quizzes.order_by('-created_at', 'id'), many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def quiz_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not IsCourseInstructor().has_object_permission(request, None, course):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = QuizSerializer(data=request.data)
    if serializer.is_valid():
        quiz = serializer.save(course=course)
        return Response(QuizSerializer(quiz).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    is_owner = _is_quiz_owner(request, quiz)

    if request.method == 'GET':
        if not is_owner and not quiz.is_published:
            return Response({'error': 'This quiz is not available'}, status=status.HTTP_403_FORBIDDEN)
        return Response(QuizSerializer(quiz).data)

    if not is_owner:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = QuizSerializer(quiz, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    quiz.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Question Views (instructor-only in this milestone) ────────────
# Student-facing question access (with correct answers stripped) and
# submission/grading are added in a later milestone alongside quiz-taking.

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def question_create(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if not _is_quiz_owner(request, quiz):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = QuestionSerializer(data=request.data)
    if serializer.is_valid():
        question = serializer.save(quiz=quiz)
        return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsInstructor])
def question_detail(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if not _is_question_owner(request, question):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(QuestionSerializer(question).data)

    if request.method == 'PUT':
        serializer = QuestionSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    question.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
