from django.utils import timezone
from rest_framework import serializers
from .models import Course, Chapter, Enrollment
from users.serializers import UserSerializer


class ChapterSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Chapter
        fields = [
            'id',
            'course',
            'title',
            'content',
            'visibility',
            'order_index'
        ]




class CourseSerializer(serializers.ModelSerializer):
    instructor = UserSerializer(read_only=True)
    chapter_count = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    chat_open = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'instructor',
            'is_published',
            'chapter_count',
            'enrolled_count',
            'chat_open',
        ]

    def get_chapter_count(self, obj):
        return obj.chapters.count()

    def get_enrolled_count(self, obj):
        return obj.enrollments.count()

    def get_chat_open(self, obj):
        # No term assigned -> no tenure concept -> chat never closes.
        # Once a term is assigned, chat closes the day after term.end_date
        # (see messaging/consumers.py for the matching write-lock enforced
        # server-side, and messaging/tasks.py for the purge job that
        # actually resets the room's history).
        if obj.term_id is None:
            return True
        return obj.term.end_date >= timezone.now().date()


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'course',
            'enrolled_at'
        ]
