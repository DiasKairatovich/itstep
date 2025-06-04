from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, CreateView, DetailView, UpdateView, DeleteView, View
from .forms import TaskForm
from .models import Task
from django.urls import reverse_lazy

class HomePageView(TemplateView):
    template_name = 'draft_app/home.html'

class TaskListView(ListView):
    model = Task
    template_name = 'draft_app/task_list.html'
    context_object_name = 'tasks'

class TaskCreateView(CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'draft_app/task_form.html'
    success_url = reverse_lazy('task_list')

class TaskDetailView(DetailView):
    model = Task
    template_name = 'draft_app/task_detail.html'
    context_object_name = 'task'

class TaskUpdateView(UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'draft_app/task_form.html'

    def get_success_url(self):
        return reverse_lazy('task_detail', kwargs={'id': self.object.id})

class TaskDeleteView(DeleteView):
    model = Task
    template_name = 'draft_app/task_delete.html'
    success_url = reverse_lazy('task_list')

class TaskCompleleView(View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        task.completed = True
        task.save()
        return redirect('task_list')

class TaskUncompleleView(View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        task.completed = False
        task.save()
        return redirect('task_list')

class TaskStatusFilterView(ListView):
    template_name = 'draft_app/task_list.html'
    context_object_name = 'tasks'
    def get_queryset(self):
        status = self.kwargs.get('status')
        if status == 'done':
            return Task.objects.filter(completed=True)
        elif status == 'pending':
            return Task.objects.filter(completed=False)
        return Task.objects.none()

class TaskSearch(ListView):
    model = Task
    template_name = 'draft_app/task_list.html'
    context_object_name = 'tasks'
    def get_queryset(self):
        query = self.request.GET.get('q')
        return Task.objects.filter(title__icontains=query) if query else Task.objects.none()
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


