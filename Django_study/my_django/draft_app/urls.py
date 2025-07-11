from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/add/', views.course_create_view, name='course_add'),
    path('courses/<int:pk>/edit/', views.course_with_lessons_view, name='course_edit'),
    path('courses/formset/', views.course_formset_view, name='course_formset'),

]