from django.urls import path
from .views import HomePageView, AboutPageView
from . import views

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('add/', views.add_product_view, name='add_product'),
    path('edit/<int:pk>/', views.edit_product_view, name='edit_product'),
    path('success/', lambda request: render(request, 'success.html'), name='product_success'),
]
