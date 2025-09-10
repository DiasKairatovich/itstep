from django.urls import path
from . import views

urlpatterns = [
    path('tasks/', views.task_list, name='task-list'),   # GET и POST тут
    path('tasks/<int:pk>/', views.task_detail, name='task-detail'),  # GET, PUT, DELETE

    path('users/', views.user_list, name='user-list'),
]
