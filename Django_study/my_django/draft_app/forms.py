from django import forms

class TaskForm(forms.Form):
    title = forms.CharField(label='task name', max_length=100)
    description = forms.TextField(label='description')
    completed = forms.BooleanField(default=False)
