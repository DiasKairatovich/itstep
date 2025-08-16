from django.db import models

# базовый абстрактный класс с полями времени
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # Эта модель не создаёт таблицу, только наследование


# ещё один абстрактный класс для адреса
class AddressModel(models.Model):
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        abstract = True  # Эта модель не создаёт таблицу, только наследование

# Последовательное наследование
class Person(TimeStampedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

# Последовательное наследование + расширение
class Employee(Person):
    employee_id = models.CharField(max_length=20)
    position = models.CharField(max_length=100)

    def get_employee_info(self):
        return f"{self.full_name()} — {self.position} (ID: {self.employee_id})"

# Двойное наследование: Manager наследует Employee и AddressModel
class Manager(Employee, AddressModel):
    department = models.CharField(max_length=100)

    def get_manager_info(self):
        return f"{self.get_employee_info()} — Руководитель отдела {self.department}, город {self.city}, страна {self.country}"
