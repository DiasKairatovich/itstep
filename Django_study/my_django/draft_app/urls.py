from django.urls import path
from .views import success_view, add_book_view

urlpatterns = [
    path('', add_book_view, name='add_book'),
    path('success/', success_view, name='success'),
]
