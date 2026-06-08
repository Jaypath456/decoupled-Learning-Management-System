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

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'instructor',
            'is_published',
            'chapter_count',
            'enrolled_count'
        ]

    def get_chapter_count(self, obj):
        return obj.chapters.count()

    def get_enrolled_count(self, obj):
        return obj.enrollments.count()


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'course',
            'enrolled_at'
        ]
