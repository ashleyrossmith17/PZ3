from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse

from .models import AcademicGroup, Course, Department, StudentProfile


class SrsPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name='Test faculty')
        cls.group = AcademicGroup.objects.create(name='Test group', department=cls.department)
        cls.course = Course.objects.create(title='Test course', department=cls.department)
        cls.student = User.objects.create_user('reader', password='Reader2026!')
        cls.student.groups.add(Group.objects.create(name='Student'))
        cls.methodist = User.objects.create_user('editor', password='Editor2026!')
        cls.methodist.groups.add(Group.objects.create(name='Methodist'))
        cls.staff = User.objects.create_user('staff', password='Staff2026!', is_staff=True)
        cls.superuser = User.objects.create_superuser('root', 'root@example.test', 'Root2026!')

    def endpoints(self):
        for name, obj in [('department', self.department), ('academic_group', self.group), ('course', self.course)]:
            yield reverse(name + '_create')
            yield reverse(name + '_update', args=[obj.pk])
            yield reverse(name + '_delete', args=[obj.pk])

    def test_all_lists_require_login(self):
        for name in ['department_list', 'academic_group_list', 'course_list', 'dashboard', 'profile']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_direct_get_and_post_guards_for_each_role(self):
        for user in [self.student, self.staff, self.superuser]:
            self.client.force_login(user)
            for url in self.endpoints():
                for method in ['get', 'post']:
                    with self.subTest(user=user.username, url=url, method=method):
                        self.assertEqual(getattr(self.client, method)(url).status_code, 403)
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_methodist_can_open_all_crud_pages(self):
        self.client.force_login(self.methodist)
        for url in self.endpoints():
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_methodist_crud_and_validation_each_entity(self):
        self.client.force_login(self.methodist)
        for name, model, payload, field in [
            ('department', Department, {'name': 'New faculty'}, 'name'),
            ('academic_group', AcademicGroup, {'name': 'New group', 'department': self.department.pk}, 'name'),
            ('course', Course, {'title': 'New course', 'description': 'Demo', 'department': self.department.pk}, 'title'),
        ]:
            self.assertEqual(self.client.post(reverse(name + '_create'), {}).status_code, 200)
            self.assertEqual(self.client.post(reverse(name + '_create'), payload).status_code, 302)
            obj = model.objects.get(**{field: payload[field]})
            payload[field] += ' edited'
            self.assertEqual(self.client.post(reverse(name + '_update', args=[obj.pk]), payload).status_code, 302)
            obj.refresh_from_db()
            self.assertEqual(getattr(obj, field), payload[field])
            self.assertEqual(self.client.get(reverse(name + '_delete', args=[obj.pk])).status_code, 200)
            self.assertTrue(model.objects.filter(pk=obj.pk).exists())
            self.assertEqual(self.client.post(reverse(name + '_delete', args=[obj.pk])).status_code, 302)
            self.assertFalse(model.objects.filter(pk=obj.pk).exists())

    def test_registration_cannot_assign_privileged_role(self):
        self.client.post(reverse('register'), {'username': 'newstudent', 'password1': 'FreshStudent2026!', 'password2': 'FreshStudent2026!', 'is_staff': 'on', 'groups': 'Methodist'})
        user = User.objects.get(username='newstudent')
        self.assertFalse(user.is_staff)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Student'])
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_staff_admin_uses_standard_model_permissions(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        self.assertEqual(self.client.get('/admin/accounts/course/').status_code, 403)
        self.staff.user_permissions.add(Permission.objects.get(codename='view_course', content_type__app_label='accounts'))
        self.assertEqual(self.client.get('/admin/accounts/course/').status_code, 200)
        self.assertEqual(self.client.get('/admin/accounts/course/add/').status_code, 403)
        self.client.force_login(self.methodist)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_role_controls_are_hidden_for_student(self):
        self.client.force_login(self.student)
        for name in ['department_list', 'academic_group_list', 'course_list']:
            response = self.client.get(reverse(name))
            self.assertNotContains(response, '/add/')
            self.assertNotContains(response, '/edit/')
            self.assertNotContains(response, '/delete/')


class SrsOrmTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='Faculty')
        self.group = AcademicGroup.objects.create(name='Group', department=self.department)
        self.user = User.objects.create_user('ormstudent')
        self.profile = StudentProfile.objects.create(user=self.user, department=self.department, academic_group=self.group)
        self.course = Course.objects.create(title='Same title', department=self.department)
        self.profile.courses.add(self.course)
        self.client.force_login(self.user)

    def test_relations_and_eager_loading_have_constant_query_cost(self):
        for index in range(5):
            user = User.objects.create_user('orm' + str(index))
            student = StudentProfile.objects.create(user=user, academic_group=self.group)
            student.courses.add(self.course)
        with self.assertNumQueries(3):
            courses = list(Course.objects.select_related('department').prefetch_related('students__user'))
            self.assertEqual(courses[0].department, self.department)
            self.assertEqual(len([student.user.username for student in courses[0].students.all()]), 6)
        with self.assertNumQueries(3):
            groups = list(AcademicGroup.objects.select_related('department').prefetch_related('students__user'))
            self.assertEqual(len([student.user.username for student in groups[0].students.all()]), 6)
        self.assertEqual(self.user.student_profile.academic_group.department, self.department)

    def test_referenced_deletions_are_protected_in_orm_and_views(self):
        for obj in [self.department, self.group, self.course]:
            with self.assertRaises(ProtectedError), transaction.atomic():
                obj.delete()
        self.user.groups.add(Group.objects.create(name='Methodist'))
        for name, obj in [('department', self.department), ('academic_group', self.group), ('course', self.course)]:
            self.assertEqual(self.client.post(reverse(name + '_delete', args=[obj.pk])).status_code, 409)
        with self.assertRaises(ProtectedError), transaction.atomic():
            Course.objects.filter(pk=self.course.pk).delete()

    def test_dashboard_counts_all_enrollments_and_keeps_duplicate_titles(self):
        for index in range(8):
            course = Course.objects.create(title='Same title' if index == 0 else 'Course ' + str(index), department=self.department)
            self.profile.courses.add(course)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['total_enrollments'], 9)
        self.assertEqual(len(response.context['chart_data']['load']['labels']), 6)
        self.assertEqual(response.context['chart_data']['load']['labels'].count('Same title'), 0)
        Course.objects.exclude(title='Same title').update(title='Z course')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['chart_data']['load']['labels'].count('Same title'), 2)
        other = Department.objects.create(name='Other')
        other_course = Course.objects.create(title='Other course', department=other)
        self.profile.courses.add(other_course)
        filtered = self.client.get(reverse('dashboard'), {'department': self.department.pk})
        self.assertEqual(filtered.context['total_enrollments'], 9)
        self.assertEqual(self.client.get(reverse('dashboard')).context['total_enrollments'], 10)
        self.profile.courses.remove(self.course)
        self.assertEqual(self.client.get(reverse('dashboard')).context['total_enrollments'], 9)
        self.assertEqual(self.client.get(reverse('dashboard'), {'department': 'bad'}).context['total_enrollments'], 9)

    def test_demo_seed_is_repeatable_and_preserves_existing_credentials(self):
        call_command('seed_demo', verbosity=0)
        before = (User.objects.count(), Course.objects.count(), StudentProfile.objects.count())
        user = User.objects.get(username='spo_staff')
        password = user.password
        call_command('seed_demo', password='Changed2026!', verbosity=0)
        self.assertEqual(before, (User.objects.count(), Course.objects.count(), StudentProfile.objects.count()))
        user.refresh_from_db()
        self.assertEqual(user.password, password)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.user_permissions.count(), 0)
