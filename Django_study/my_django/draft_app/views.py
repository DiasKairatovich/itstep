from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
import requests
from .forms import ProductForm
from django.core.paginator import Paginator
from .models import Product

class HomePageView(View):
    def get(self, request):
        products = Product.objects.all()
        paginator = Paginator(products, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'main.html', {'page_obj': page_obj})

class AboutPageView(View):
    def get(self, request):
        # Получаем посты
        response = requests.get('https://jsonplaceholder.typicode.com/posts')
        posts = response.json()

        paginator = Paginator(posts, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'about.html', {'page_obj': page_obj})

def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            # Задание 8: save(commit=False)
            product = form.save(commit=False)

            # Задание 6: Работа с cleaned_data
            print("Название:", form.cleaned_data['title'])
            print("Категории:", form.cleaned_data['categories'])
            print("Изменённые поля:", form.changed_data)

            product.save()
            form.save_m2m()  # сохранение связей many-to-many
            return redirect('success')
    else:
        form = ProductForm()

    return render(request, 'add_product.html', {'form': form})

def edit_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ProductForm(instance=product)

    return render(request, 'edit_product.html', {'form': form, 'product': product})