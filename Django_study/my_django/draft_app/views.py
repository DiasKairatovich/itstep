from django.views import View
from django.shortcuts import render
import requests
from django.core.paginator import Paginator

class HomePageView(View):
    def get(self, request):
        return render(request, 'main.html')

class AboutPageView(View):
    def get(self, request):
        # Получаем посты
        response = requests.get('https://jsonplaceholder.typicode.com/posts')
        posts = response.json()

        # Ручное деление
        chunk_size = 5
        chunk1 = posts[0:5]
        chunk2 = posts[5:10]
        chunk3 = posts[10:15]

        context = {
            'chunk1': chunk1,
            'chunk2': chunk2,
            'chunk3': chunk3,
        }

        return render(request, 'title.html', context)
