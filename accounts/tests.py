from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Course, Department, StudentProfile


class AuthPagesTests(TestCase):
    def test_home_page_opens(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Учебный портал Django')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_user_can_register(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'student',
                'email': 'student@example.com',
                'password1': 'PracticePass2026!',
                'password2': 'PracticePass2026!',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        self.assertTrue(User.objects.filter(username='student').exists())

    def test_user_can_login(self):
        User.objects.create_user(username='student', password='PracticePass2026!')

        response = self.client.post(
            reverse('login'),
            {'username': 'student', 'password': 'PracticePass2026!'},
        )

        self.assertRedirects(response, reverse('profile'))


class CourseOrmTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student1',
            password='Student123!',
        )
        self.department = Department.objects.create(
            name='Информационные технологии',
        )
        self.course = Course.objects.create(
            title='Веб-программирование',
            description='Разработка веб-приложений',
            department=self.department,
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            department=self.department,
        )
        self.profile.courses.add(self.course)

    def test_related_objects_are_available(self):
        self.assertEqual(self.department.courses.first(), self.course)
        self.assertEqual(self.profile.courses.first(), self.course)
        self.assertEqual(self.course.students.first(), self.profile)
        self.assertEqual(self.user.student_profile, self.profile)

    def test_course_list_requires_login(self):
        response = self.client.get(reverse('course_list'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_authorized_user_can_open_course_list(self):
        self.client.login(username='student1', password='Student123!')

        response = self.client.get(reverse('course_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Веб-программирование')
        self.assertContains(response, 'Информационные технологии')

    def test_dashboard_uses_database_aggregates_and_filter(self):
        other_department = Department.objects.create(name='Математика')
        Course.objects.create(title='Дискретная математика', department=other_department)
        self.client.login(username='student1', password='Student123!')

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_courses'], 2)
        self.assertContains(response, 'Курсы по факультетам')
        self.assertIn('Веб-программирование', response.context['chart_data']['load']['labels'])

        filtered = self.client.get(reverse('dashboard'), {'department': self.department.pk})
        self.assertEqual(filtered.context['total_courses'], 1)
        self.assertEqual(filtered.context['total_students'], 1)
