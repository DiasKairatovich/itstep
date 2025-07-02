from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class IceCream(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    available = models.BooleanField(default=False)
    date = models.DateField(auto_now=True)

    def __str__(self):
        return self.title

