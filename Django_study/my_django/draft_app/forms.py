from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'description', 'price', 'available', 'categories']
        labels = {
            'title': 'Название товара',
            'description': 'Описание',
            'price': 'Цена',
            'available': 'Доступен',
            'categories': 'Категории',
        }
        help_texts = {
            'title': 'Введите краткое название продукта',
            'description': 'Подробное описание продукта',
            'price': 'Укажите цену в тенге',
            'available': 'Отметьте, если товар в наличии',
            'categories': 'Выберите одну или несколько категорий',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'categories': forms.SelectMultiple(attrs={
                'size': 6,
                'class': 'form-control'
            }),
        }

    def clean_title(self):
        title = self.cleaned_data['title']
        if not title.strip():
            raise forms.ValidationError("Название не может состоять только из пробелов.")
        return title

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 100:
            raise forms.ValidationError("Цена не может быть ниже 100.")
        return price

    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        required=False
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput,
        required=False
    )
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Пароли не совпадают!')