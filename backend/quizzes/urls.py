from django.urls import path

from . import views

urlpatterns = [
    # quizzes
    path('courses/<int:course_id>/quizzes/', views.quiz_list),
    path('courses/<int:course_id>/quizzes/create/', views.quiz_create),
    path('quizzes/<int:quiz_id>/', views.quiz_detail),
    # questions
    path('quizzes/<int:quiz_id>/questions/create/', views.question_create),
    path('questions/<int:question_id>/', views.question_detail),
]
