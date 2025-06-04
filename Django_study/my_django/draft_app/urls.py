from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'), # СТАЛО CBV
    path('tasks/', views.TaskListView.as_view(), name='task_list'), # СТАЛО CBV
    path('task/create/', views.TaskCreateView.as_view(), name='create_task'), # СТАЛО CBV
    path('task/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'), # СТАЛО CBV
    path('task/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='edit_task'), # СТАЛО CBV
    path('task/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='delete_task'), # СТАЛО CBV
    path('tasks/status/<str:status>/', views.TaskStatusFilterView.as_view(), name='filter_by_status'), # СТАЛО CBV
    path('task/<int:id>/complete/', views.TaskCompleleView.as_view(), name='complete_task'), # СТАЛО CBV
    path('task/<int:id>/uncomplete/', views.TaskUncompleleView.as_view(), name='uncomplete_task'), # СТАЛО CBV
    path('tasks/search/', views.TaskSearch.as_view(), name='search_tasks'), # СТАЛО CBV

    path('first_user/', views.FirstUserView.as_view(), name='first_user'),
]

