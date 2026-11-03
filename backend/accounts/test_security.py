import json
import tempfile
from datetime import timedelta
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.db import connection, close_old_connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.utils import timezone

from .models import AccountSecurity, LoginThrottle
from .testing import verified_force_login
from create_template.models import Template


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class LoginThrottleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alice', email='alice@example.com', password='ValidPassword123',
        )
        AccountSecurity.objects.create(user=self.user, email_verified=True)

    def attempt(self, client=None, username='alice', password='incorrect'):
        client = client or self.client
        return client.post('/api/auth/login/', json.dumps({
            'username': username, 'password': password,
        }), content_type='application/json')

    def test_sixth_attempt_is_blocked_before_password_or_email(self):
        for _ in range(5):
            self.assertEqual(self.attempt().status_code, 401)
        response = self.attempt(password='ValidPassword123')
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(LoginThrottle.objects.get().attempts, 5)

    def test_independent_clients_share_one_database_limit(self):
        other = Client()
        for client in [self.client, other, self.client, other, self.client]:
            self.assertEqual(self.attempt(client).status_code, 401)
        self.assertEqual(self.attempt(other).status_code, 429)
        self.assertEqual(LoginThrottle.objects.count(), 1)

    def test_expired_window_allows_correct_credentials_and_still_requires_otp(self):
        for _ in range(5):
            self.attempt()
        LoginThrottle.objects.update(window_started_at=timezone.now() - timedelta(minutes=11))
        response = self.attempt(password='ValidPassword123')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['step'], 'login')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)
        self.assertEqual(LoginThrottle.objects.get().attempts, 1)

    def test_unknown_username_is_also_limited_and_case_variants_share_limit(self):
        for username in ['missing', 'MISSING', 'Missing', 'missing', 'MISSING']:
            self.assertEqual(self.attempt(username=username).status_code, 401)
        self.assertEqual(self.attempt(username='missing').status_code, 429)
        bucket = LoginThrottle.objects.get()
        self.assertEqual(len(bucket.key), 64)
        self.assertNotIn('missing', bucket.key)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class StaffMfaTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='moderator', password='ValidPassword123', is_staff=True,
        )

    def test_staff_session_without_mfa_cannot_read_or_modify_moderation(self):
        self.client.force_login(self.admin)
        self.assertFalse(self.client.get('/api/moderation/me/').json()['isAdmin'])
        self.assertEqual(self.client.get('/api/moderation/users/').status_code, 401)
        response = self.client.post('/api/moderation/templates/1/hide/',
                                    json.dumps({'reason': 'test'}), content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_verified_staff_session_can_access_moderation(self):
        verified_force_login(self.client, self.admin)
        self.assertTrue(self.client.get('/api/moderation/me/').json()['isAdmin'])
        self.assertEqual(self.client.get('/api/moderation/users/').status_code, 200)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class UploadEndpointTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        setting = override_settings(MEDIA_ROOT=self.media.name)
        setting.enable()
        self.addCleanup(setting.disable)
        self.user = get_user_model().objects.create_user(
            username='uploader', email='uploader@example.com', password='ValidPassword123',
        )
        verified_force_login(self.client, self.user)

    def template_payload(self, image):
        return {
            'title': 'Safe images',
            'criteria': json.dumps([{'name': 'Quality', 'weight': 1}]),
            'items': json.dumps([{'name': 'An item'}]),
            'item_image_0': image,
        }

    def test_fake_image_is_rejected_before_creating_template(self):
        image = SimpleUploadedFile('photo.png', b'<script>alert(1)</script>', content_type='image/png')
        response = self.client.post('/api/templates/', self.template_payload(image))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Template.objects.count(), 0)

    def test_valid_image_with_html_suffix_and_payload_is_stored_as_clean_png(self):
        output = BytesIO()
        Image.new('RGB', (2, 2), 'red').save(output, format='PNG')
        marker = b'<script>private-upload-marker</script>'
        image = SimpleUploadedFile('photo.html', output.getvalue() + marker, content_type='image/png')
        response = self.client.post('/api/templates/', self.template_payload(image))
        self.assertEqual(response.status_code, 201, response.content)
        item = Template.objects.get(pk=response.json()['id']).items.get()
        self.assertRegex(item.image.name, r'^template_items/[0-9a-f]{32}\.png$')
        with item.image.open('rb') as stored:
            data = stored.read()
        self.assertNotIn(marker, data)
        with Image.open(BytesIO(data)) as clean:
            self.assertEqual(clean.format, 'PNG')
            self.assertEqual(clean.size, (2, 2))

    def test_invalid_avatar_does_not_partially_change_password(self):
        image = SimpleUploadedFile('avatar.png', b'not an image', content_type='image/png')
        response = self.client.post('/api/auth/profile/', {
            'avatar': image, 'password': 'ReplacementPassword456',
        })
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ValidPassword123'))


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL row locking required')
class ConcurrentLoginThrottleTests(TransactionTestCase):
    def test_six_connections_reserve_only_five_attempts(self):
        from .throttling import reserve_login_attempt
        barrier = Barrier(6)

        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return reserve_login_attempt('concurrent-login-check')
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(attempt, range(6)))
        self.assertEqual(results.count(0), 5)
        self.assertEqual(sum(result > 0 for result in results), 1)
        self.assertEqual(LoginThrottle.objects.get().attempts, 5)
