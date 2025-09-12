from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskListCreateAPIView, TaskDetailAPIView, TaskViewSet, UserViewSet

# Роутер для ViewSet
router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # APIView для задач
    path('tasks-class/', TaskListCreateAPIView.as_view(), name='task-list-create'),
    path('tasks-class/<int:pk>/', TaskDetailAPIView.as_view(), name='task-detail'),

    # Метаконтроллеры (tasks + users)
    path('', include(router.urls)),
]