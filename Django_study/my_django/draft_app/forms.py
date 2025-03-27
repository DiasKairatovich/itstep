from django import forms
from .models import Contact

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact # Определяем, с какой моделью связана форма
        fields = ["name", "email", "message"] # Указываем, какие поля использовать

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label="Имя пользователя")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")