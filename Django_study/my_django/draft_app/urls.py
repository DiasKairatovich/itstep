from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import upload_image, upload_success, home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("upload/", upload_image, name="upload_image"),
    path("success/<int:pk>/", upload_success, name="upload_success"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
