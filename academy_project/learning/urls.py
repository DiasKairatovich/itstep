from django.urls import path
from . import views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', views.UserDataView.as_view(), name='user_form'),
    path('redirect/', RedirectView.as_view(pattern_name='index'), name='user_redirect'),
    path('home/', views.index, name='index'),

    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('enroll/', views.enroll_student, name='enroll_student'),
]
