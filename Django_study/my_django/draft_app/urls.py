from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_tasks, name='task_list'),
    path('task/create/', views.create_task, name='create_task'),
    path('task/<int:id>/', views.view_task, name='task_detail'),
    path('task/<int:id>/edit/', views.edit_task, name='edit_task'),
    path('task/<int:id>/delete/', views.delete_task, name='delete_task'),
    path('task/<int:id>/complete/', views.complete_task, name='complete_task'),
    path('task/<int:id>/uncomplete/', views.uncomplete_task, name='uncomplete_task'),
    path('tasks/status/<str:status>/', views.filter_by_status, name='filter_by_status'),
    path('tasks/search/', views.search_tasks, name='search_tasks'),
]

