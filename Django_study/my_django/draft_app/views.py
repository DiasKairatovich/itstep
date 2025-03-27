from django.shortcuts import render
from .forms import ContactForm

def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()  # Сохраняем данные в базе
            return render(request, "contact_success.html")
    else:
        form = ContactForm()

    return render(request, "contact.html", {"form": form})

def contact_success(request):
    return render(request, "contact_success.html")  # Отображаем страницу успеха
