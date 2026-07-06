from rest_framework import serializers

from .models import Question, Quiz


class QuizSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id',
            'course',
            'title',
            'description',
            'is_published',
            'question_count',
            'created_at',
        ]

    def get_question_count(self, obj):
        return obj.questions.count()


class QuestionSerializer(serializers.ModelSerializer):
    """Full question representation, including correct answers - used by
    instructor-facing endpoints only. The student-facing sanitized view
    (which strips correct-answer keys before a quiz is taken) is added in
    a later milestone alongside quiz-taking itself.
    """

    quiz = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Question
        fields = [
            'id',
            'quiz',
            'question_type',
            'body',
            'points',
            'order_index',
        ]

    def validate(self, attrs):
        question_type = attrs.get(
            'question_type', getattr(self.instance, 'question_type', Question.SINGLE_CHOICE)
        )
        body = attrs.get('body', getattr(self.instance, 'body', None))

        if not isinstance(body, dict):
            raise serializers.ValidationError({'body': 'body must be a JSON object.'})

        if question_type in (Question.SINGLE_CHOICE, Question.MULTIPLE_CHOICE):
            self._validate_choice_body(question_type, body)
        elif question_type == Question.SHORT_ANSWER:
            self._validate_short_answer_body(body)

        return attrs

    def _validate_choice_body(self, question_type, body):
        options = body.get('options')
        if not isinstance(options, list) or not options:
            raise serializers.ValidationError(
                {'body': 'options must be a non-empty list for choice questions.'}
            )

        option_ids = set()
        for option in options:
            if not isinstance(option, dict) or 'id' not in option or 'text' not in option:
                raise serializers.ValidationError(
                    {'body': 'each option must be an object with "id" and "text".'}
                )
            option_ids.add(option['id'])

        correct_option_ids = body.get('correct_option_ids')
        if not isinstance(correct_option_ids, list) or not correct_option_ids:
            raise serializers.ValidationError(
                {'body': 'correct_option_ids must be a non-empty list for choice questions.'}
            )

        if not set(correct_option_ids).issubset(option_ids):
            raise serializers.ValidationError(
                {'body': 'correct_option_ids must only reference ids present in options.'}
            )

        if question_type == Question.SINGLE_CHOICE and len(set(correct_option_ids)) != 1:
            raise serializers.ValidationError(
                {'body': 'single_choice questions must have exactly one correct_option_id.'}
            )

    def _validate_short_answer_body(self, body):
        correct_answer = body.get('correct_answer')
        if not isinstance(correct_answer, str) or not correct_answer.strip():
            raise serializers.ValidationError(
                {'body': 'correct_answer must be a non-empty string for short_answer questions.'}
            )
