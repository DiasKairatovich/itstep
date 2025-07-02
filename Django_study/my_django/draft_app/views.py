from django.views import View
from django.shortcuts import render

class HomePageView(View):
    def get(self, request):
        return render(request, 'main.html')

class AboutPageView(View):
    def get(self, request):
        return render(request, 'title.html')