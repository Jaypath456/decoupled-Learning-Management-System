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
    # student quiz-taking
    path('quizzes/<int:quiz_id>/take/', views.quiz_take),
    path('quizzes/<int:quiz_id>/submit/', views.quiz_submit),
    path('quizzes/<int:quiz_id>/my-result/', views.quiz_my_result),
    # live sessions (room lifecycle)
    path('quizzes/<int:quiz_id>/sessions/', views.session_create),
    path('sessions/<str:room_code>/', views.session_detail),
    path('sessions/<str:room_code>/start/', views.session_start),
    path('sessions/<str:room_code>/end/', views.session_end),
]
