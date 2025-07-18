from django import forms
from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'price', 'description', 'category']
        labels = {
            'title': 'Name of the course',
            'price': 'Cost of the course',
            'description': 'Explanation of the course',
            'category': 'Category type',
        }
        help_texts = {
            'title': 'Enter name of course',
            'price': 'Enter the cost of course',
            'description': 'Enter short description of the course',
            'category': 'Choose category type',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 5, 'cols': 40}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and not (10000 <= price <= 100000):
            raise forms.ValidationError("Price must be between 10,000 and 100,000")
        return price

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title and len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long")
        return title
