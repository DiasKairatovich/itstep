from django.shortcuts import render
from .models import Author, Book, Reader

def about_view(request):
    return render(request, "draft_app/about.html")

def home_view(request):
    books = Book.objects.all() # получаем все объекты из БД по таблице Book
    return render(request, "draft_app/home.html", {'books': books})

def contacts_view(request):
    return render(request, "draft_app/contacts.html")



