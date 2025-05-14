from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Task
from .forms import TaskForm
import csv

def home(request):
    return render(request, 'home.html')

def view_tasks(request):
    tasks = Task.objects.all()
    return render(request, 'task_list.html', {'tasks': tasks})

def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm()
    return render(request, 'task_form.html', {'form': form})

def view_task(request, id):
    task = get_object_or_404(Task, id=id)
    return render(request, 'task_detail.html', {'task': task})

def edit_task(request, id):
    task = get_object_or_404(Task, id=id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_detail', id=id)
    else:
        form = TaskForm(instance=task)
    return render(request, 'task_form.html', {'form': form})

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
    return render(request, 'task_list.html', {'tasks': tasks})

def export_csv(request):
    tasks = Task.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tasks.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Название', 'Описание', 'Выполнено'])

    for task in tasks:
        writer.writerow([task.id, task.title, task.description, task.completed])

    return response

def import_csv(request):
    if request.method == 'POST' and request.FILES.get('file'):
        csv_file = request.FILES['file'].read().decode('utf-8').splitlines()
        reader = csv.DictReader(csv_file)
        for row in reader:
            Task.objects.create(
                title=row['Название'],
                description=row.get('Описание', ''),
                completed=row['Выполнено'].lower() == 'true'
            )
        return redirect('task_list')
    return render(request, 'import_form.html')

def search_tasks(request):
    query = request.GET.get('q')
    tasks = Task.objects.filter(title__icontains=query) if query else []
    return render(request, 'task_list.html', {'tasks': tasks, 'query': query})


