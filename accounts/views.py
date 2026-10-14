from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AcademicGroupForm, CourseForm, DepartmentForm, RegisterForm
from .models import AcademicGroup, Course, Department, StudentProfile
from .permissions import is_methodist, methodist_required


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
    student = StudentProfile.objects.select_related('department', 'academic_group__department').prefetch_related('courses').filter(user=request.user).first()
    return render(request, 'accounts/profile.html', {'student': student, 'roles': request.user.groups.all(), 'is_methodist': is_methodist(request.user)})


@login_required
def course_list(request):
    courses = Course.objects.select_related('department').prefetch_related('students__user').all()
    return render(request, 'accounts/course_list.html', {'courses': courses, 'is_methodist': is_methodist(request.user)})


@login_required
def department_list(request):
    departments = Department.objects.annotate(course_count=Count('courses', distinct=True), group_count=Count('academic_groups', distinct=True))
    return render(request, 'accounts/department_list.html', {'departments': departments, 'is_methodist': is_methodist(request.user)})


@login_required
def academic_group_list(request):
    groups = AcademicGroup.objects.select_related('department').prefetch_related('students__user')
    return render(request, 'accounts/academic_group_list.html', {'groups': groups, 'is_methodist': is_methodist(request.user)})


def crud_views(model, form_class, list_name, label):
    @methodist_required
    @require_http_methods(['GET', 'POST'])
    def edit(request, pk=None):
        obj = get_object_or_404(model, pk=pk) if pk is not None else None
        form = form_class(request.POST if request.method == 'POST' else None, instance=obj)
        if request.method == 'POST' and form.is_valid():
            form.save()
            return redirect(list_name)
        return render(request, 'accounts/object_form.html', {'form': form, 'title': ('Изменить ' if obj else 'Добавить ') + label, 'list_name': list_name})

    @methodist_required
    @require_http_methods(['GET', 'POST'])
    def delete(request, pk):
        obj = get_object_or_404(model, pk=pk)
        error = ''
        if request.method == 'POST':
            if isinstance(obj, Course) and obj.students.exists():
                error = 'Нельзя удалить курс, на который записаны студенты.'
            else:
                try:
                    with transaction.atomic():
                        obj.delete()
                    return redirect(list_name)
                except ProtectedError:
                    error = 'Нельзя удалить объект: существуют связанные записи.'
        return render(request, 'accounts/object_confirm_delete.html', {'object': obj, 'title': 'Удалить ' + label, 'list_name': list_name, 'error': error}, status=409 if error else 200)
    return edit, delete


department_create, department_delete = crud_views(Department, DepartmentForm, 'department_list', 'факультет')
department_update = department_create
academic_group_create, academic_group_delete = crud_views(AcademicGroup, AcademicGroupForm, 'academic_group_list', 'учебную группу')
academic_group_update = academic_group_create
course_create, course_delete = crud_views(Course, CourseForm, 'course_list', 'курс')
course_update = course_create


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
    enrollments = courses.annotate(enrollment_count=Count('students')).aggregate(total=Sum('enrollment_count'))['total'] or 0
    course_load = list(courses.values('pk', 'title').annotate(total=Count('students')).order_by('-total', 'title', 'pk')[:6])
    chart_data = {
        'courses': {'labels': [item.name for item in course_counts], 'values': [item.total for item in course_counts]},
        'students': {'labels': [item.name for item in student_counts], 'values': [item.total for item in student_counts]},
        'load': {'labels': [item['title'] for item in course_load], 'values': [item['total'] for item in course_load]},
    }
    return render(request, 'accounts/dashboard.html', {
        'departments': departments, 'selected_department': str(selected.pk) if selected else '',
        'total_courses': courses.count(), 'total_departments': chart_departments.count(),
        'total_students': profiles.count(), 'total_enrollments': enrollments,
        'chart_data': chart_data,
    })
