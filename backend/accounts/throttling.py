"""Database-backed login limits shared by all Django workers."""
import hashlib
import math
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import LoginThrottle

ATTEMPT_LIMIT = 5
WINDOW = timedelta(minutes=10)


def reserve_login_attempt(username):
    """Reserve an attempt before checking a password; return retry seconds or 0."""
    key = hashlib.sha256(username.casefold().encode('utf-8')).hexdigest()
    with transaction.atomic():
        LoginThrottle.objects.get_or_create(key=key)
        bucket = LoginThrottle.objects.select_for_update().get(key=key)
        now = timezone.now()
        if bucket.window_started_at + WINDOW <= now:
            bucket.window_started_at = now
            bucket.attempts = 0
        if bucket.attempts >= ATTEMPT_LIMIT:
            return max(1, math.ceil((bucket.window_started_at + WINDOW - now).total_seconds()))
        bucket.attempts += 1
        bucket.save(update_fields=['attempts', 'window_started_at'])
    return 0
