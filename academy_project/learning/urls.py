from django.urls import path
from . import views
from django.shortcuts import render

urlpatterns = [
    path('home/', views.index, name='index'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('enroll/', views.enroll_student, name='enroll_student'),

    path('', views.login_view, name='login'),
    path('empty_login/', lambda request: render(request, 'learning/empty_login.html'), name='empty_login'),
]
