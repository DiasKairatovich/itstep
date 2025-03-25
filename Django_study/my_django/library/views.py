from django.shortcuts import render
from .models import Book

def book_list(request):
    books = Book.objects.select_related('author').all()  # Загружаем книги вместе с авторами
    context = {'books': books} # для того что бы HTML понимал с чем работать
    return render(request, 'library/book_list.html', context) # Передаем данные в шаблон HTML
