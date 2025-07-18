from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.manage_products, name='manage_products'),
    path('success/', views.success, name='success'),
]