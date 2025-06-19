from django.urls import path
from .views import HomePageView, UserListView, UserDetailView

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('user/', UserDetailView.as_view(), name='user_detail'),
]
