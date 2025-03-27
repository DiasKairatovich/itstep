from django.shortcuts import render
from .forms import ContactForm, LoginForm

def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()  # Сохраняем данные в базе
            return render(request, "draft_app/success.html")
    else:
        form = ContactForm()

    return render(request, "draft_app/contact.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            print(f"Пользователь: {username}, Пароль: {password}")  # Просто заглушка
            return render(request, "draft_app/success.html")  # Перенаправляем на стр. успеха
    else:
        form = LoginForm()

    return render(request, "draft_app/login.html", {"form": form})

def home_view(request):
    return render(request, "draft_app/home.html")

def success(request):
    return render(request, "draft_app/success.html")

