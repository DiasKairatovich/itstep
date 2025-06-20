from django.urls import path
from .views import HomePageView, UserListView, UserDetailView

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('users/', UserListView.as_view(), name='users_list'),
    path('users/<slug:username>/', UserDetailView.as_view(), name='user_detail'),
]
