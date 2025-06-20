from re import search
from django.views import View
from django.shortcuts import render
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView

class HomePageView(View):
    def get(self, request):
        return render(request, 'home.html')

class UserListView(ListView):
    model = User
    template_name = 'users_list.html'
    context_object_name = 'users'
    ordering = ['-date_joined']  # для хронологического списка (от новых к старым)

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')

        if search_query:
            queryset = queryset.filter(username__icontains=search_query)

        return queryset


class UserDetailView(DetailView):
    model = User
    template_name = 'user_detail.html'
    context_object_name = 'user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
