from rest_framework.response import Response
from rest_framework import status, viewsets
from .models import Task
from .serializers import TaskSerializer, UserSerializer
from django.contrib.auth.models import User
from rest_framework.views import APIView

class TaskListCreateAPIView(APIView): # Обновленный task_list !!!
    def get(self, request):
        tasks = Task.objects.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskDetailAPIView(APIView): # Обновленный task_detail контроллер-класс для одной задачи !!!
    def get_object(self, pk):
        try:
            return Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return None

    def get(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    def put(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TaskSerializer(task, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response(status=status.HTTP_404_NOT_FOUND)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskViewSet(viewsets.ModelViewSet): # Метаконтроллер для задач !!!
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

class UserViewSet(viewsets.ModelViewSet): # Метаконтроллер для пользователей !!!
    queryset = User.objects.all()
    serializer_class = UserSerializer
