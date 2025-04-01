from django.shortcuts import render

def about_view(request):
    return render(request, "draft_app/about.html")

def home_view(request):
    return render(request, "draft_app/home.html")

def contacts_view(request):
    return render(request, "draft_app/contacts.html")



