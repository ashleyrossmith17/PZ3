from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db.models.deletion import ProtectedError


class Department(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='courses',
    )

    def __str__(self):
        return self.title


class AcademicGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='academic_groups')

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
    )
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name='students',
    )
    academic_group = models.ForeignKey(
        AcademicGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='students',
    )

    def __str__(self):
        return self.user.username


@receiver(pre_delete, sender=Course)
def protect_enrolled_course(sender, instance, using, **kwargs):
    students = instance.students.using(using).all()
    if students.exists():
        raise ProtectedError('Enrolled courses cannot be deleted.', students)
