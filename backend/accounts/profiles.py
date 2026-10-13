from uuid import uuid4

from .models import User_profile
from .models import AccountSecurity


def current_profile(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None
    if request.session.get('auth_mfa_user') != user.pk:
        return None
    if not AccountSecurity.objects.filter(user=user, email_verified=True).exists():
        return None
    return ensure_profile(user)


def ensure_profile(user):
    # Never claim an unrelated legacy profile based on its editable display name.
    email = user.email
    if not email or User_profile.objects.filter(email=email).exclude(user=user).exists():
        email = f'{uuid4().hex}@profiles.invalid'
    profile, _ = User_profile.objects.get_or_create(
        user=user,
        defaults={
            'userName': user.username,
            'email': email,
            'password': user.password,
        },
    )
    return profile
