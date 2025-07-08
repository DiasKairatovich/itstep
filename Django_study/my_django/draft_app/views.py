from django.shortcuts import render, redirect
from .forms import BookForm

def add_book_view(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success')
    else:
        form = BookForm()

    return render(request, 'main.html', {'form': form})

def success_view(request):
    return render(request, 'success.html')