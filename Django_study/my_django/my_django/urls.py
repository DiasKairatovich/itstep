from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('draft_app.urls')), # Подключаем маршруты из приложения "draft_app"
    path('api/', include('drf_app.urls')), # Подключаем маршруты api "drf_app"
    path('login/', obtain_auth_token, name='api-login'),  # доступен без авторизации
]
