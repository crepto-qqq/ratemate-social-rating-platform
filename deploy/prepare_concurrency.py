"""Create five temporary authenticated fixtures; stdout is PRIVATE session data."""
import json
import os
import sys
from importlib import import_module
from uuid import uuid4

sys.path.insert(0, '/app')
import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.db import connection, transaction
from accounts.models import AccountSecurity
from accounts.profiles import ensure_profile

with connection.cursor() as cursor:
    cursor.execute('SELECT current_user')
    assert cursor.fetchone()[0] == 'ratemate_migrator', 'Use the migration service.'

User = get_user_model()
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
tag = 'a3load_' + uuid4().hex[:12]
fixtures = []
with transaction.atomic():
    for number in range(1, 6):
        username = f'{tag}_{number}'
        user = User(username=username, email=f'{username}@example.invalid', is_active=True)
        user.set_unusable_password()
        user.save()
        AccountSecurity.objects.create(user=user, email_verified=True)
        ensure_profile(user)
        session = SessionStore()
        session[SESSION_KEY] = str(user.pk)
        session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session['auth_mfa_user'] = user.pk
        session.set_expiry(600)
        session.save()
        fixtures.append({'id': user.pk, 'username': username, 'session_key': session.session_key})
json.dump({'tag': tag, 'cookie_name': settings.SESSION_COOKIE_NAME, 'users': fixtures}, sys.stdout)
print()
