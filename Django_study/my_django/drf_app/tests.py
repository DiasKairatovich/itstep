from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import User
from .models import Task

class TaskAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="tester")

    def test_create_task(self):
        response = self.client.post("/api/tasks/", {"title": "Купить хлеб"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "Купить хлеб")

    def test_get_tasks(self):
        Task.objects.create(title="Проверка", description="Тест")
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
