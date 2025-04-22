from django.db import models
from django.core.validators import MinValueValidator

class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    def __str__(self):
        return f"{self.first_name}  {self.last_name}"

    def book_info(self): # Метод для получения количества книг, написанных автором
        return self.books.count() # работает через related_name !!!

# Таблица книг в БД
class Book(models.Model):
    CATEGORY_CHOICES = [
        ('fiction', 'Fiction'),
        ('nonfiction', 'Non-fiction'),
        ('fantasy', 'Fantasy'),
        ('sci-fi', 'Science Fiction'),
        ('mystery', 'Mystery'),
        ('biography', 'Biography'),
        ('history', 'History'),
        ('education', 'Education'),
    ]

    genre = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='fiction')

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, related_name='books', on_delete=models.CASCADE)
    published_date = models.DateField()
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)] # Не менее 0.01
    )
    def __str__(self):
        return self.title

    def book_info(self):
        return f"Book ID: {self.id} Title: {self.title} Price: {self.price}"

    def reader_count(self): # Метод для получения количества читателей, которые прочитали эту книгу
        return self.readers.count() # работает через related_name !!!

# Таблица читателей в БД
class Reader(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    books_read = models.ManyToManyField(Book, related_name='readers')
    def __str__(self):
        return f"{self.first_name}  {self.last_name}"

    def books_read_count(self):
        return self.books_read.count()

    def books_info(self): # Метод для получения информации о прочитанных книгах
        return [book.book_info() for book in self.books_read.all()] # работает через related_name !!!
