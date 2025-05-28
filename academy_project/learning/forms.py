from django import forms
from .models import Student, Course

class EnrollmentForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.all(), label="Студент")
    course = forms.ModelChoiceField(queryset=Course.objects.all(), label="Курс")