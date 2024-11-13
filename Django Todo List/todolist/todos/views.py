from lib2to3.fixes.fix_input import context
from typing import Dict, Any

from django.http import Http404
from django.template.defaultfilters import title

from .models import Todo
from django.shortcuts import render, redirect


def index(request):
    todos = Todo.objects.all()[:10]

    context1 = {'todos': todos}

    return render(request, template_name='index.html', context=context1)

def detail(request, todo_id):
    todo = Todo.objects.get(pk=todo_id)

    context2 = {'todo': todo}

    return render(request, template_name='detail.html', context=context2)

def add(request):
    if request.method == 'POST':
        title = request.POST['title']
        text = request.POST['text']

        todo = Todo(title=title, text=text)
        todo.save()

        return redirect('index') #if successfully saved redirects to main page
    else:
        return render(request, 'add.html')