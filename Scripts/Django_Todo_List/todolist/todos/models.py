from datetime import datetime

from django.db import models

# Здесь создается модель действия на странице сайте, например Туду создает обьект с заголовком и основным текстом
# также время устанавливет текущее, еще добавлена функция которая присваевает созданному обьекту названия из заголовка
class Todo(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    created_at = models.DateTimeField(default=datetime.now, blank=True)
    def __str__(self):
        return self.title