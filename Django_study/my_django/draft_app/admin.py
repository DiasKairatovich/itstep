from django.contrib import admin
from .models import Author, Book, Reader

admin.site.register(Author) # Регистрируем модель Author
admin.site.register(Book) # Регистрируем модель Book
admin.site.register(Reader) # Регистрируем модель Reader
