from django import forms
from .models import Contact

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact # Определяем, с какой моделью связана форма
        fields = ["name", "email", "message"] # Указываем, какие поля использовать