from django import forms
from .models import BorrowRecord
class ReturnBookForm(forms.ModelForm):
    class Meta:
        model = BorrowRecord
        fields = ['book']