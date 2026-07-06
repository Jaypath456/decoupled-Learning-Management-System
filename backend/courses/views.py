from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from lms_project.safe_cache import safe_delete, safe_get, safe_set
from .models import Course, Chapter, Enrollment
from .serializers import (
    CourseSerializer, 
    ChapterSerializer, 
    EnrollmentSerializer
)
from .permissions import IsInstructor, IsStudent

# ─── Course Views ─────────────────────────────────────────────

# Short TTL: this is a read-heavy, low-staleness-tolerance cache (a newly
# published/unpublished course should show up reasonably quickly), not a
# long-lived cache. Invalidated explicitly on every write path that can
# change catalog membership (course_create, course_detail's PUT/DELETE)
# so the TTL is really just a safety net, not the primary consistency
# mechanism.
CATALOG_CACHE_KEY = 'course_catalog:published'
CATALOG_CACHE_TTL_SECONDS = 60


def _invalidate_catalog_cache():
    safe_delete(CATALOG_CACHE_KEY)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_list(request):
    cached = safe_get(CATALOG_CACHE_KEY)
    if cached is not None:
        return Response(cached)

    courses = Course.objects.filter(is_published=True).select_related('instructor', 'term')
    serializer = CourseSerializer(courses, many=True)
    safe_set(CATALOG_CACHE_KEY, serializer.data, CATALOG_CACHE_TTL_SECONDS)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInstructor])
def instructor_courses(request):
    courses = Course.objects.filter(instructor=request.user).select_related('instructor', 'term')
    serializer = CourseSerializer(courses, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def course_create(request):
    serializer = CourseSerializer(data=request.data)
    if serializer.is_valid():
        course = serializer.save(instructor=request.user)
        # A new course could be created already-published, so the
        # catalog cache must be invalidated unconditionally rather than
        # only when is_published=True.
        _invalidate_catalog_cache()
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def course_detail(request, course_id):
    course = get_object_or_404(Course.objects.select_related('instructor', 'term'), id=course_id)

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
            # Covers both is_published toggling and title/description
            # edits, which the cached catalog response also contains.
            _invalidate_catalog_cache()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    course.delete()
    _invalidate_catalog_cache()
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
    enrollments = Enrollment.objects.filter(student=request.user).select_related(
        'course', 'course__instructor', 'course__term'
    )
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