from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from courses.models import Course
from courses.permissions import IsCourseInstructor, IsInstructor, IsStudent

from .models import Break, Section, Term
from .serializers import BreakSerializer, SectionSerializer, TermSerializer


def _is_section_owner(request, section):
    return IsCourseInstructor().has_object_permission(request, None, section)


# ─── Term Views ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def term_list(request):
    terms = Term.objects.all()
    return Response(TermSerializer(terms, many=True).data)


# ─── Section Views ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def section_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    sections = Section.objects.filter(course=course).select_related('term').prefetch_related('meetings')

    term_id = request.query_params.get('term')
    if term_id:
        sections = sections.filter(term_id=term_id)

    return Response(SectionSerializer(sections.order_by('term', 'section_code'), many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInstructor])
def section_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not IsCourseInstructor().has_object_permission(request, None, course):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = SectionSerializer(data=request.data)
    if serializer.is_valid():
        section = serializer.save(course=course)
        return Response(SectionSerializer(section).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def section_detail(request, section_id):
    section = get_object_or_404(Section, id=section_id)

    if request.method == 'GET':
        return Response(SectionSerializer(section).data)

    if not _is_section_owner(request, section):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = SectionSerializer(section, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    section.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Break Views (student-owned only) ────────────────────────
# Instructors don't get Breaks - their equivalent "don't double-book me"
# constraint is derived from their own Meetings by the schedule
# generation engine (a later milestone), not a second concept here.

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsStudent])
def break_list_create(request):
    if request.method == 'GET':
        breaks = Break.objects.filter(student=request.user)
        return Response(BreakSerializer(breaks, many=True).data)

    serializer = BreakSerializer(data=request.data)
    if serializer.is_valid():
        brk = serializer.save(student=request.user)
        return Response(BreakSerializer(brk).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsStudent])
def break_delete(request, break_id):
    # Scoped by student=request.user in the lookup itself (rather than a
    # fetch-then-check), so a break belonging to another student 404s
    # instead of leaking a 403 that would confirm the id exists.
    brk = get_object_or_404(Break, id=break_id, student=request.user)
    brk.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
