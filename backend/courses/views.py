from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Course, Chapter, Enrollment
from .serializers import (
    CourseSerializer, 
    ChapterSerializer, 
    EnrollmentSerializer
)
from .permissions import IsInstructor, IsStudent, IsCourseInstructor, IsEnrolled

# ─── Course Views ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_list(request):
    courses = Course.objects.filter(is_published=True).select_related('instructor')
    serializer = CourseSerializer(courses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInstructor])
def instructor_courses(request):
    courses = Course.objects.filter(instructor=request.user).select_related('instructor')
    serializer = CourseSerializer(courses, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def course_create(request):
    serializer = CourseSerializer(data=request.data)
    if serializer.is_valid():
        course = serializer.save(instructor=request.user)
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    is_owner = IsCourseInstructor().has_object_permission(request, None, course)

    if request.method == 'GET':
        if not course.is_published and not is_owner:
            return Response({'error': 'This course is not available'}, status=status.HTTP_403_FORBIDDEN)
        return Response(CourseSerializer(course).data)

    # Permission check for modifying/deleting
    if not is_owner:
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

    if not IsCourseInstructor().has_object_permission(request, None, course):
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
    is_owner = IsCourseInstructor().has_object_permission(request, None, chapter)

    if request.method == 'GET':
        if is_owner:
            return Response(ChapterSerializer(chapter).data)

        is_enrolled = IsEnrolled().has_object_permission(request, None, chapter)
        if chapter.course.is_published and chapter.visibility == 'public' and is_enrolled:
            return Response(ChapterSerializer(chapter).data)

        return Response({'error': 'This chapter is not available'}, status=status.HTTP_403_FORBIDDEN)

    if not is_owner:
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
@permission_classes([IsAuthenticated, IsStudent])
def manage_enrollment(request, course_id):
    if request.method == 'POST':
        # Only published courses can be joined - draft courses are not
        # available to students even if they know the course id.
        course = get_object_or_404(Course, id=course_id, is_published=True)
        Enrollment.objects.get_or_create(student=request.user, course=course)
        return Response({"message": "Enrolled"}, status=status.HTTP_201_CREATED)

    # DELETE: allow unenrolling even if the course was unpublished after
    # the student joined.
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.filter(student=request.user, course=course).delete()
    return Response({"message": "Unenrolled"}, status=status.HTTP_204_NO_CONTENT)


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
    } for e in enrollments]

    return Response(data)