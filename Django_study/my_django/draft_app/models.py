from django.db import models

class Book(models.Model):
 title = models.CharField(max_length=200)
 author = models.CharField(max_length=100)
 published_year = models.PositiveIntegerField()
 price = models.DecimalField(max_digits=8, decimal_places=2)

class Sale(models.Model):
 product_name = models.CharField(max_length=100)
 quantity = models.PositiveIntegerField()
 sale_date = models.DateField()
 revenue = models.DecimalField(max_digits=10, decimal_places=2)

class Department(models.Model):
 name = models.CharField(max_length=100)

class Employee(models.Model):
 department = models.ForeignKey(Department, on_delete=models.CASCADE)
 name = models.CharField(max_length=100)
 salary = models.PositiveIntegerField()

 class Meta:
  indexes = [
   models.Index(fields=['salary'], name='salary_idx'),
  ]


