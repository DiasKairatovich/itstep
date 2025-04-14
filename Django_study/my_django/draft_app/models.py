from django.db import models

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
        return self.title # Отображение объекта в админке

# Таблица читателей в БД
class Reader(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    books = models.ManyToManyField(Book) # Reader теперь имеет связь ManyToManyField с Book
    def __str__(self):
        return f"{self.first_name}  {self.last_name}" # Отображение объекта в админке

