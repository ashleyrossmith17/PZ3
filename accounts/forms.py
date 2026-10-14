from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django import forms
from django.db import transaction

from .models import AcademicGroup, Course, Department, StudentProfile


class RegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.groups.add(Group.objects.get_or_create(name='Student')[0])
            StudentProfile.objects.create(user=user)
        return user


class StyledLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'


class DepartmentForm(StyledModelForm):
    class Meta:
        model = Department
        fields = ('name',)
        labels = {'name': 'Название факультета'}


class AcademicGroupForm(StyledModelForm):
    class Meta:
        model = AcademicGroup
        fields = ('name', 'department')
        labels = {'name': 'Учебная группа', 'department': 'Факультет'}


class CourseForm(StyledModelForm):
    class Meta:
        model = Course
        fields = ('title', 'description', 'department')
        labels = {'title': 'Название курса', 'description': 'Описание', 'department': 'Факультет'}
