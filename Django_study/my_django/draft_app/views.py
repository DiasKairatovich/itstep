from django.shortcuts import render
from .models import Book

def home_view(request):
    books = Book.objects.all() # получаем все объекты из БД по таблице Book
    return render(request, "draft_app/home.html", {'books': books})

def static_page_view(request, page):
    # оптимизация вьюшек для простого рендеринга статичных страниц Contacts и About
    return render(request, f"draft_app/{page}.html")




