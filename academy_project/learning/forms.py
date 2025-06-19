from django import forms
from .models import Student, Course

class EnrollmentForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.all(), label="Студент")
    course = forms.ModelChoiceField(queryset=Course.objects.all(), label="Курс")



class UserDataForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
