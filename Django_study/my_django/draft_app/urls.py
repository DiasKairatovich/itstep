from django.urls import path

from .views import home_view, static_page_view

urlpatterns = [
    path('', home_view, name="home_page"),
    path('about/', static_page_view, {'page': 'about'}, name='about_page'),
    path('contacts/', static_page_view, {'page': 'contacts'}, name='contacts_page'),
]
