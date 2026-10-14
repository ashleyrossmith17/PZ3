from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def is_methodist(user):
    return user.is_authenticated and user.is_active and user.groups.filter(name='Methodist').exists()


def methodist_required(view):
    @login_required
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not is_methodist(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return guarded
