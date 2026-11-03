"""Remove only the temporary users, their test data, sessions and uploaded files."""
import json
import sys
from pathlib import Path

sys.path.insert(0, '/app')
import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from create_template.models import Item

manifest = json.load(sys.stdin)
assert len(manifest['users']) == 5
assert manifest['tag'].startswith('a3load_')
with connection.cursor() as cursor:
    cursor.execute('SELECT current_user')
    assert cursor.fetchone()[0] == 'ratemate_migrator', 'Use the migration service.'

User = get_user_model()
ids = []
for fixture in manifest['users']:
    assert fixture['username'].startswith(manifest['tag'] + '_')
    user = User.objects.filter(pk=fixture['id']).first()
    if user is not None:
        assert user.username == fixture['username']
        assert user.email.endswith('@example.invalid')
        assert not user.is_staff and not user.is_superuser
        ids.append(user.pk)

media_root = Path(settings.MEDIA_ROOT).resolve()
images = list(Item.objects.filter(template__owner__user_id__in=ids).values_list('image', flat=True))
paths = []
for name in images:
    if name:
        path = (media_root / name).resolve()
        assert path.is_relative_to(media_root), 'Unexpected media path'
        paths.append(path)

with transaction.atomic():
    Session.objects.filter(session_key__in=[u['session_key'] for u in manifest['users']]).delete()
    User.objects.filter(pk__in=ids).delete()
for path in paths:
    path.unlink(missing_ok=True)
assert not User.objects.filter(pk__in=[u['id'] for u in manifest['users']]).exists()
print(f'PASS: removed {len(ids)} temporary users, their sessions and business data, and {len(paths)} test images.')
