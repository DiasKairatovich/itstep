from django.views import View
from django.shortcuts import render
from django.contrib.auth.models import User

class HomePageView(View):
    def get(self, request):
        return render(request, 'home.html')

class UserListView(View):
    def get(self, request):
        users = User.objects.all()
        return render(request, 'users_list.html', {'users': users})

class UserDetailView(View):
    def get(self, request):
        username = request.GET.get('username')
        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = None
        return render(request, 'user_detail.html', {'user': user})
