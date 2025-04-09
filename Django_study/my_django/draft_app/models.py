from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.db import models

class Human(models.Model):
    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    age = models.IntegerField()

    class Meta:
        abstract = True

class Child(Human):
    hobby = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.second_name}"

class IceCream(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Kiosk(models.Model):
    place = models.CharField(max_length=200)
    ice_creams = models.ManyToManyField(IceCream)

    def __str__(self):
        return self.place












class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    price = models.FloatField(validators=[MinValueValidator(0.0)])
    stock = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('delivered', 'Доставлен'),
        ('canceled', 'Отменен'),
    ]
    id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    total_price = models.FloatField(validators=[MinValueValidator(0.0)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Заказ №{self.id} - {self.status}"

class Article(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=500)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    published_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

# Таблица авторов в БД
class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()

    def __str__(self):
        return f"{self.first_name}  {self.last_name}"  # Отображение объекта в админке

# Таблица книг в БД
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE) # Book теперь ссылается на Author через ForeignKey
    published_date = models.DateField()

    def __str__(self):
        return self.title

# Таблица читателей в БД
class Reader(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    books = models.ManyToManyField(Book) # Reader теперь имеет связь ManyToManyField с Book

    def __str__(self):
        return f"{self.first_name}  {self.last_name}"


class BorrowRecord(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    def is_returned(self):
        return self.returned_at is not None

    def __str__(self):
        return f"{self.reader.name} - {self.book.title}"




