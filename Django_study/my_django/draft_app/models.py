from django.db import models

class UploadedImage(models.Model):
    original = models.ImageField(upload_to='images/originals/')
    thumbnail = models.ImageField(upload_to='images/thumbnails/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Photo(models.Model):
    image = models.ImageField(upload_to='photos/')
