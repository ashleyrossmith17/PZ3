from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from .forms import RegisterForm
from .models import Course, Department, StudentProfile


def home(request):
    return render(request, 'accounts/home.html')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def course_list(request):
    courses = Course.objects.select_related('department').all()
    return render(request, 'accounts/course_list.html', {'courses': courses})


@login_required
def dashboard(request):
    departments = Department.objects.all()
    selected_id = request.GET.get('department', '')
    selected = departments.filter(pk=selected_id).first() if selected_id.isdecimal() else None
    courses = Course.objects.all()
    profiles = StudentProfile.objects.select_related('department').all()
    chart_departments = departments
    if selected:
        courses = courses.filter(department=selected)
        profiles = profiles.filter(department=selected)
        chart_departments = departments.filter(pk=selected.pk)
    course_counts = list(chart_departments.annotate(total=Count('courses')))
    student_counts = list(chart_departments.annotate(total=Count('students')))
    course_load = list(courses.values('title').annotate(total=Count('students')).order_by('-total', 'title')[:6])
    chart_data = {
        'courses': {'labels': [item.name for item in course_counts], 'values': [item.total for item in course_counts]},
        'students': {'labels': [item.name for item in student_counts], 'values': [item.total for item in student_counts]},
        'load': {'labels': [item['title'] for item in course_load], 'values': [item['total'] for item in course_load]},
    }
    return render(request, 'accounts/dashboard.html', {
        'departments': departments, 'selected_department': str(selected.pk) if selected else '',
        'total_courses': courses.count(), 'total_departments': chart_departments.count(),
        'total_students': profiles.count(), 'total_enrollments': sum(item['total'] for item in course_load),
        'chart_data': chart_data,
    })
