from django import forms
from .models import Product, Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'price']
        labels = {
            'title': 'Name of the book',
            'price': 'Cost of the book',
        }
        help_texts = {
            'title': 'Enter name of book',
            'price': 'Enter the cost of book',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
        }