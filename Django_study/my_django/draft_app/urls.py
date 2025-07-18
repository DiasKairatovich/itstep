from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', views.manage_products, name='manage_products'),
    path('success/', views.success, name='success'),

    path('user-info/', views.user_info, name='user_info'),
]