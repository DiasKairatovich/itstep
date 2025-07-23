from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, Lesson
from .forms import CourseForm
from django.forms import modelformset_factory, inlineformset_factory
from django.utils import timezone
from .models import Product
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login


@login_required
def profile_view(request):
    user = request.user
    context = {
        'user': user,
        'is_superuser': user.is_superuser,
        'groups': user.groups.all(),
        'permissions': user.get_all_permissions(),
    }
    return render(request, 'profile.html', context)

@login_required
@permission_required('auth.change_user', raise_exception=True)
def edit_profile_view(request):
    return render(request, 'edit_profile.html')

@login_required
@permission_required('auth.change_user', raise_exception=True)
def secure_view(request):
    return render(request, 'secure_page.html')

def manage_products(request):
    ProductFormSet = modelformset_factory(Product, fields=('name', 'price'), extra=2)

    if request.method == 'POST':
        formset = ProductFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('success')
    else:
        formset = ProductFormSet(queryset=Product.objects.all())

    return render(request, 'manage_products.html', {'formset': formset})

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # авто-вход
            return redirect('profile')  # или 'manage_products'
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})




def success(request):
    return render(request, 'success.html')

def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'course_detail.html', {'course': course})

def course_create_view(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.published = timezone.now()  # добавляем дату публикации
            course.save()
            return redirect('course_list')
    else:
        form = CourseForm()

    return render(request, 'course_form.html', {'form': form})


def course_formset_view(request):
    CourseFormSet = modelformset_factory(
        Course,
        form=CourseForm,
        extra=0,
        max_num=10,
    )

    if request.method == 'POST':
        formset = CourseFormSet(request.POST, queryset=Course.objects.all()[:10])
        if formset.is_valid():
            formset.save()
            return redirect('course_list')
    else:
        formset = CourseFormSet(queryset=Course.objects.all()[:10])

    return render(request, 'course_formset.html', {'formset': formset})

def course_with_lessons_view(request, pk=None):
    LessonInlineFormSet = inlineformset_factory(
        Course,
        Lesson,
        fields=['title', 'video_link'],
        extra=1,
        max_num=5,
        can_delete=False
    )

    if pk:
        course = get_object_or_404(Course, pk=pk)
    else:
        course = None

    if request.method == 'POST':
        course_form = CourseForm(request.POST, instance=course)
        formset = LessonInlineFormSet(request.POST, instance=course)


        if course_form.is_valid() and formset.is_valid():
            course = course_form.save()
            formset.instance = course
            formset.save()

            return redirect(course.get_absolute_url())
    else:
        course_form = CourseForm(instance=course)
        formset = LessonInlineFormSet(instance=course)

    return render(request, 'course_with_lessons.html', {
        'course_form': course_form,
        'formset': formset
    })