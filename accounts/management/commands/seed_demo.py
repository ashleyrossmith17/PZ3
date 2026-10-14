from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import AcademicGroup, Course, Department, StudentProfile


class Command(BaseCommand):
    help = 'Create reproducible local demo accounts and academic data; preserve existing users.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='DemoSPO2026!', help='Password for newly created demo accounts only.')

    @transaction.atomic
    def handle(self, *args, **options):
        student_role, _ = Group.objects.get_or_create(name='Student')
        methodist_role, _ = Group.objects.get_or_create(name='Methodist')
        methodist_role.permissions.add(*Permission.objects.filter(content_type__app_label='accounts'))
        users = {}
        for name, role, staff, superuser in [
            ('spo_student', student_role, False, False),
            ('spo_methodist', methodist_role, False, False),
            ('spo_staff', None, True, False),
            ('spo_admin', None, True, True),
        ]:
            user, created = User.objects.get_or_create(username=name)
            if created:
                user.set_password(options['password'])
                user.is_staff, user.is_superuser = staff, superuser
                user.email = name + '@example.test'
                user.save()
                if role:
                    user.groups.add(role)
            users[name] = user
        department, _ = Department.objects.get_or_create(name='Информационные технологии')
        math, _ = Department.objects.get_or_create(name='Математика')
        group, _ = AcademicGroup.objects.get_or_create(name='М3О-236БВ-25', defaults={'department': department})
        AcademicGroup.objects.get_or_create(name='М3О-237БВ-25', defaults={'department': math})
        profile, _ = StudentProfile.objects.get_or_create(user=users['spo_student'], defaults={'department': department, 'academic_group': group})
        for index, title in enumerate(['Веб-программирование', 'Базы данных', 'Алгоритмы', 'Операционные системы', 'Сети', 'Тестирование', 'Проектирование ПО', 'Веб-программирование']):
            course, _ = Course.objects.get_or_create(title=title, department=math if index == 7 else department, defaults={'description': 'Учебный курс СПО'})
            profile.courses.add(course)
        self.stdout.write(self.style.SUCCESS('Demo ready: spo_student, spo_methodist, spo_staff, spo_admin. Existing passwords and privileges are unchanged.'))
