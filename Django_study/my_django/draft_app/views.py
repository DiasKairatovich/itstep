from django.shortcuts import render, redirect, get_object_or_404
from .forms import TaskForm
from django.http import JsonResponse
from .models import Task

def get_tasks(request):
    tasks = [
        {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'completed': task.completed
        }
        for task in Task.objects.all()
    ]
    return JsonResponse(tasks, safe=False)

def home(request):
    return render(request, 'draft_app/home.html')


def view_tasks(request):
    tasks = Task.objects.all()
    return render(request, 'draft_app/task_list.html', {'tasks': tasks})

def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm()
    return render(request, 'draft_app/task_form.html', {'form': form})

def view_task(request, id):
    task = get_object_or_404(Task, id=id)
    return render(request, 'draft_app/task_detail.html', {'task': task})

def edit_task(request, id):
    task = get_object_or_404(Task, id=id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_detail', id=id)
    else:
        form = TaskForm(instance=task)
    return render(request, 'draft_app/task_form.html', {'form': form})

def delete_task(request, id):
    task = get_object_or_404(Task, id=id)
    task.delete()
    return redirect('task_list')

def complete_task(request, id):
    task = get_object_or_404(Task, id=id)
    task.completed = True
    task.save()
    return redirect('task_list')

def uncomplete_task(request, id):
    task = get_object_or_404(Task, id=id)
    task.completed = False
    task.save()
    return redirect('task_list')

def filter_by_status(request, status):
    if status == 'done':
        tasks = Task.objects.filter(completed=True)
    elif status == 'pending':
        tasks = Task.objects.filter(completed=False)
    else:
        tasks = []
    return render(request, 'draft_app/task_list.html', {'tasks': tasks})

def search_tasks(request):
    query = request.GET.get('q')
    tasks = Task.objects.filter(title__icontains=query) if query else []
    return render(request, 'draft_app/task_list.html', {'tasks': tasks, 'query': query})


