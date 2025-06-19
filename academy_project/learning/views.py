from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .models import Student, Course, Enrollment

from .forms import EnrollmentForm, UserDataForm
from django.views.generic.edit import FormView
from django.views.generic.base import RedirectView
from django.urls import reverse_lazy

class UserDataView(FormView):
    template_name = 'learning/user_form.html'
    form_class = UserDataForm
    success_url = reverse_lazy('user_redirect')



def index(request):
    courses = Course.objects.all()
    course_data = []
    for course in courses:
        student_count = Enrollment.objects.filter(course=course).count()  # подсчёт студентов для каждого курса
        course_data.append({'course': course, 'student_count': student_count})
    return render(request, 'learning/index.html', {'course_data': course_data})

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    students = Student.objects.filter(enrollment__course=course)

    #передаем весь список студентов для формы
    all_students = Student.objects.exclude(id__in=students.values_list('id', flat=True))
    context = {
        'course': course,
        'students': students,
        'all_students': all_students
    }
    return render(request, "learning/course_detail.html", context)

def enroll_student(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            course = form.cleaned_data['course']

            if Enrollment.objects.filter(student=student, course=course).exists():
                messages.error(request, 'Данный студент уже записан на этот курс')
            else:
                Enrollment.objects.create(student=student, course=course)
                messages.success(request, 'Студент успешно записан')
                return redirect('index')  # лучше редиректить по имени урла, не на файл

    else:
        form = EnrollmentForm()

    return render(request, 'learning/enroll_student.html', {'form': form})