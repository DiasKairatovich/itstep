from django.urls import path

from .views import about_view, home_view, contacts_view

urlpatterns = [
    path('', home_view, name="home_page"),
    path('about/', about_view, name="about_page"),
    path('contacts', contacts_view, name="contacts_page"),
]
