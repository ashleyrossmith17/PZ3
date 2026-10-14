from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('courses/', views.course_list, name='course_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

for prefix, name in [('departments', 'department'), ('groups', 'academic_group'), ('courses', 'course')]:
    if name != 'course':
        urlpatterns.append(path(f'{prefix}/', getattr(views, f'{name}_list'), name=f'{name}_list'))
    urlpatterns.extend([
        path(f'{prefix}/add/', getattr(views, f'{name}_create'), name=f'{name}_create'),
        path(f'{prefix}/<int:pk>/edit/', getattr(views, f'{name}_update'), name=f'{name}_update'),
        path(f'{prefix}/<int:pk>/delete/', getattr(views, f'{name}_delete'), name=f'{name}_delete'),
    ])
