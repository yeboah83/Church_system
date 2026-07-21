from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles):
    """
    Decorator for views that checks whether the logged-in user has a role 
    included in allowed_roles. Super Admin is always allowed.
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role in allowed_roles or request.user.role == 'Super Admin' or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f"Access Denied: Your role ({request.user.role}) does not have permission to access that page.")
                return redirect('dashboard')
        return wrapped_view
    return decorator
