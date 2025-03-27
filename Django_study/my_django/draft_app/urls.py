from django.urls import path
from .views import contact_view, success, login_view, home_view

urlpatterns = [
    path('contact/', contact_view, name="contact_page"), # Страница сохранения контактов
    path("success/", success, name="success_page"), # Страница успеха
    path('login/', login_view, name="login_page"), # Страница авторизации пользователя
    path('', home_view, name="home_page") # Главная страница приложения
]