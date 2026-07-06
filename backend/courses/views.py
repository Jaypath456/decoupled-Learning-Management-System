from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Course, Chapter, Enrollment
from .pagination import StandardResultsPagination
from .serializers import (
    CourseSerializer, 
    ChapterSerializer, 
    EnrollmentSerializer
)
from .permissions import IsInstructor, IsStudent


def _with_course_counts(queryset):
    """Annotates chapter_count/enrolled_count on a Course queryset with a
    single GROUP BY query, instead of CourseSerializer issuing two COUNT
    queries per course (see CourseSerializer.get_chapter_count/
    get_enrolled_count for the fallback used when a queryset isn't
    annotated, e.g. nested course objects reached via my_courses)."""
    return queryset.annotate(
        chapter_count=Count('chapters', distinct=True),
        enrolled_count=Count('enrollments', distinct=True),
    )


# ─── Course Views ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_list(request):
    # Course.Meta.ordering (-created_at) isn't a unique key - courses
    # created in the same request/transaction can share a timestamp,
    # which would make paginated results unstable across page fetches
    # (Django warns about this: UnorderedObjectListWarning). Adding `id`
    # as a tiebreaker keeps ordering fully deterministic without touching
    # the model's default ordering.
    courses = _with_course_counts(
        Course.objects.filter(is_published=True)
        .select_related('instructor')
        .order_by('-created_at', 'id')
    )

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(courses, request)
    serializer = CourseSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInstructor])
def instructor_courses(request):
    # Deliberately not paginated: the Dashboard/CourseList frontend pages
    # compute aggregate stats (total published, total students) across the
    # instructor's *entire* course list, and an instructor's own course
    # count is bounded by what they personally author - unlike the public
    # catalog, this isn't a platform-wide growth concern.
    courses = _with_course_counts(
        Course.objects.filter(instructor=request.user).select_related('instructor')
    )
    serializer = CourseSerializer(courses, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def course_create(request):
    serializer = CourseSerializer(data=request.data)
    if serializer.is_valid():
        course = serializer.save(instructor=request.user)
        # Re-fetch through the annotated queryset so the response uses the
        # same annotated code path as every other CourseSerializer usage,
        # instead of relying on the fallback .count() queries for this one
        # case (a freshly created course has 0 chapters/enrollments either
        # way, but this keeps the behavior consistent and query-cheap).
        course = _with_course_counts(Course.objects.filter(pk=course.pk)).get()
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def course_detail(request, course_id):
    course = get_object_or_404(_with_course_counts(Course.objects.all()), id=course_id)

    if request.method == 'GET':
        if not course.is_published and course.instructor != request.user:
            return Response({'error': 'This course is not available'}, status=status.HTTP_403_FORBIDDEN)
        return Response(CourseSerializer(course).data)

    # Permission check for modifying/deleting
    if course.instructor != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = CourseSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    course.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Chapter Views ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chapter_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if course.instructor == request.user:
        chapters = Chapter.objects.filter(course=course)
    elif course.is_published:
        chapters = Chapter.objects.filter(course=course, visibility='public')
    else:
        return Response({'error': 'This course is not available'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ChapterSerializer(chapters.order_by('order_index', 'id'), many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def chapter_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if course.instructor != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ChapterSerializer(data=request.data)
    if serializer.is_valid():
        chapter = serializer.save(course=course)
        return Response(ChapterSerializer(chapter).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def chapter_detail(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)

    if request.method == 'GET':
        if chapter.course.instructor == request.user:
            return Response(ChapterSerializer(chapter).data)

        is_enrolled = Enrollment.objects.filter(student=request.user, course=chapter.course).exists()
        if chapter.course.is_published and chapter.visibility == 'public' and is_enrolled:
            return Response(ChapterSerializer(chapter).data)

        return Response({'error': 'This chapter is not available'}, status=status.HTTP_403_FORBIDDEN)

    if chapter.course.instructor != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = ChapterSerializer(chapter, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    chapter.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Enrollment Views ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudent])
def enroll(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_published=True)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return Response({'error': 'Already enrolled in this course'}, status=status.HTTP_400_BAD_REQUEST)

    enrollment = Enrollment.objects.create(student=request.user, course=course)
    return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudent])
def my_courses(request):
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__instructor')
    serializer = EnrollmentSerializer(enrollments, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudent])
def enrollment_status(request, course_id):
    enrolled = Enrollment.objects.filter(student=request.user, course_id=course_id).exists()
    return Response({'enrolled': enrolled})

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_enrollment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        Enrollment.objects.get_or_create(student=request.user, course=course)
        return Response({"message": "Enrolled"}, status=201)
        
    if request.method == 'DELETE':
        Enrollment.objects.filter(student=request.user, course=course).delete()
        return Response({"message": "Unenrolled"}, status=204)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInstructor])
def course_enrolled_students(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    # Get all enrollments for this course
    enrollments = Enrollment.objects.filter(course=course).select_related('student')
    
    # Extract student data
    data = [{
        "id": e.student.id,
        "name": e.student.username,
        "email": e.student.email,
        "phone": getattr(e.student, 'phone_number', 'N/A') 
    } for e in enrollments]
    
    return Response(data)