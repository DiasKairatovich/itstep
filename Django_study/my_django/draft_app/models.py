from django.db import models
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    title = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    published = models.DateTimeField()
    category = models.ForeignKey(Category, related_name='courses', on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('course_detail', args=[self.pk])

    def is_recent(self):
        return self.published >= timezone.now() - timedelta(days=7)

    class Meta:
        db_table = 'catalog_course'
        ordering = ['-published']

class Lesson(models.Model):
    title = models.CharField(max_length=100)
    video_link = models.URLField()
    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)

    def __str__(self):
        return self.title