from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('draft_app.urls')), # Подключаем маршруты из приложения "draft_app"
    path('api/', include('drf_app.urls')), # Подключаем маршруты api "drf_app"
]
