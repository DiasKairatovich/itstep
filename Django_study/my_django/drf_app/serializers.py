from rest_framework import serializers
from .models import Task
from django.contrib.auth.models import User

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"

    # Поле title не должно быть пустым
    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Название задачи не может быть пустым")
        return value

    # Кастомная валидация всех данных
    def validate(self, data):
        if "ошибка" in data.get("description", "").lower():
            raise serializers.ValidationError("Описание не должно содержать слово 'ошибка'")
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}  # пароль не будет отображаться в ответе
        }

    # Проверка имени пользователя
    def validate_username(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Имя пользователя должно содержать минимум 3 символа")
        return value

    # Проверка email
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Этот email уже используется")
        return value

    # Проверка всех данных (например, длина пароля)
    def validate(self, data):
        if len(data.get("password", "")) < 6:
            raise serializers.ValidationError("Пароль должен содержать минимум 6 символов")
        return data

    # Создание пользователя с хэшированным паролем
    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', '')
        )
        user.set_password(validated_data['password'])  # хэшируем пароль
        user.save()
        return user