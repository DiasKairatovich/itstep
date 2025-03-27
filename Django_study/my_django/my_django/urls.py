from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('library/', include('library.urls')), # Подключаем маршруты из приложения "library"
    path('draft/', include('draft_app.urls')), # Подключаем маршруты из приложения "draft_app"
]
