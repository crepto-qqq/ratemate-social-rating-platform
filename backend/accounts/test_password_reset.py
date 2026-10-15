import json
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import AccountSecurity, OtpChallenge, User_profile


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.old_password = 'OldStrongPass123'
        self.user = get_user_model().objects.create_user(
            username='alice', email='alice@example.com', password=self.old_password,
        )
        AccountSecurity.objects.create(user=self.user, email_verified=True)
        User_profile.objects.create(
            user=self.user, userName='Alice', email=self.user.email,
            password=self.user.password,
        )

    def post(self, path, data, *, csrf=True):
        headers = {}
        if csrf:
            token = self.client.get('/api/auth/csrf/').json()['csrfToken']
            headers['HTTP_X_CSRFTOKEN'] = token
        return self.client.post(path, json.dumps(data), content_type='application/json', **headers)

    def request_reset(self, email='alice@example.com'):
        return self.post('/api/auth/password-reset/request/', {'email': email})

    def code(self):
        return re.search(r'\b\d{6}\b', mail.outbox[-1].body).group()

    def test_request_hides_whether_email_exists_and_requires_csrf(self):
        self.assertEqual(self.post('/api/auth/password-reset/request/', {'email': self.user.email}, csrf=False).status_code, 403)
        known = self.request_reset()
        self.assertEqual(known.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('password reset', mail.outbox[0].subject.lower())
        unknown = self.request_reset('nobody@example.com')
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(set(known.json()), set(unknown.json()))
        self.assertEqual(known.json()['detail'], unknown.json()['detail'])
        self.assertNotEqual(known.json()['challengeId'], unknown.json()['challengeId'])

    def test_reset_code_changes_password_once_and_invalidates_login_codes(self):
        old_login = self.post('/api/auth/login/', {'username': 'alice', 'password': self.old_password})
        self.assertEqual(old_login.status_code, 200)
        reset = self.request_reset().json()
        code = self.code()
        new_password = 'NewStrongPass456'
        response = self.post('/api/auth/password-reset/confirm/', {
            'challengeId': reset['challengeId'], 'code': code, 'password': new_password,
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password(self.old_password))
        self.assertEqual(User_profile.objects.get(user=self.user).password, self.user.password)
        self.assertFalse(OtpChallenge.objects.filter(user=self.user, consumed=False).exists())
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', {
            'challengeId': reset['challengeId'], 'code': code, 'password': 'AnotherStrong789',
        }).status_code, 400)
        self.assertEqual(self.post('/api/auth/verify/', {
            'challengeId': old_login.json()['challengeId'], 'code': '000000',
        }).status_code, 400)
        self.assertEqual(self.post('/api/auth/login/', {'username': 'alice', 'password': self.old_password}).status_code, 401)
        self.assertEqual(self.post('/api/auth/login/', {'username': 'alice', 'password': new_password}).json()['step'], 'login')

    def test_reset_code_cannot_be_used_as_login_code(self):
        reset = self.request_reset().json()
        response = self.post('/api/auth/verify/', {
            'challengeId': reset['challengeId'], 'code': self.code(),
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)

    def test_rejects_weak_password_wrong_code_and_repeated_requests(self):
        reset = self.request_reset().json()
        code = self.code()
        self.assertEqual(self.request_reset().status_code, 429)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', {
            'challengeId': reset['challengeId'], 'code': code, 'password': 'weak',
        }).status_code, 400)
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(5):
            self.assertEqual(self.post('/api/auth/password-reset/confirm/', {
                'challengeId': reset['challengeId'], 'code': wrong, 'password': 'NewStrongPass456',
            }).status_code, 400)
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', {
            'challengeId': reset['challengeId'], 'code': code, 'password': 'NewStrongPass456',
        }).status_code, 429)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.old_password))

    def test_code_is_session_bound_and_expires(self):
        reset = self.request_reset().json()
        code = self.code()
        other = Client(enforce_csrf_checks=True)
        token = other.get('/api/auth/csrf/').json()['csrfToken']
        response = other.post('/api/auth/password-reset/confirm/', json.dumps({
            'challengeId': reset['challengeId'], 'code': code, 'password': 'NewStrongPass456',
        }), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        OtpChallenge.objects.filter(pk=reset['challengeId']).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', {
            'challengeId': reset['challengeId'], 'code': code, 'password': 'NewStrongPass456',
        }).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.old_password))

    def test_unverified_account_gets_the_same_public_response_without_email(self):
        AccountSecurity.objects.filter(user=self.user).update(email_verified=False)
        unverified = self.request_reset()
        self.assertEqual(unverified.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        cache.clear()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        disabled = self.request_reset()
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(unverified.json()['detail'], disabled.json()['detail'])
        self.assertEqual(len(mail.outbox), 0)
