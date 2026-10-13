import json
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings

from .models import AccountSecurity, OtpChallenge


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.password = 'StrongPass123'

    def post(self, path, data):
        token = self.client.get('/api/auth/csrf/').json()['csrfToken']
        return self.client.post(path, json.dumps(data), content_type='application/json', HTTP_X_CSRFTOKEN=token)

    def code(self):
        return re.search(r'\b\d{6}\b', mail.outbox[-1].body).group()

    def test_registration_activation_and_login_require_distinct_codes(self):
        response = self.post('/api/auth/register/', {'username': 'alice', 'email': 'alice@example.com', 'password': self.password})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['step'], 'activation')
        user = get_user_model().objects.get(username='alice')
        self.assertFalse(user.is_active)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)
        activation = self.code()
        self.assertNotIn(activation, response.content.decode())
        response = self.post('/api/auth/verify/', {'challengeId': response.json()['challengeId'], 'code': activation})
        self.assertEqual(response.json()['step'], 'login_required')
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)
        response = self.post('/api/auth/login/', {'username': 'alice', 'password': self.password})
        self.assertEqual(response.json()['step'], 'login')
        otp = self.code()
        challenge_id = response.json()['challengeId']
        wrong = '000000' if otp != '000000' else '111111'
        self.assertEqual(self.post('/api/auth/verify/', {'challengeId': challenge_id, 'code': wrong}).status_code, 400)
        self.assertEqual(self.post('/api/auth/verify/', {'challengeId': challenge_id, 'code': otp}).json()['step'], 'authenticated')
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 200)
        self.assertEqual(self.post('/api/auth/verify/', {'challengeId': challenge_id, 'code': otp}).status_code, 400)
        self.assertEqual(self.post('/api/auth/logout/', {}).status_code, 200)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)

    def test_rejects_missing_email_weak_password_and_duplicate_email(self):
        for email, password in [('', self.password), ('alice@example.com', 'weakpass1'), ('bad', self.password)]:
            response = self.post('/api/auth/register/', {'username': 'alice', 'email': email, 'password': password})
            self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(self.post('/api/auth/register/', {'username': 'alice', 'email': 'alice@example.com', 'password': self.password}).status_code, 201)
        response = self.post('/api/auth/register/', {'username': 'bob', 'email': 'ALICE@example.com', 'password': self.password})
        self.assertEqual(response.status_code, 409)

    def test_legacy_account_must_enroll_email(self):
        user = get_user_model().objects.create_user(username='legacy', password=self.password)
        response = self.post('/api/auth/login/', {'username': 'legacy', 'password': self.password})
        self.assertEqual(response.json()['step'], 'email_required')
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)
        response = self.post('/api/auth/enroll-email/', {'email': 'legacy@example.com'})
        self.assertEqual(response.json()['step'], 'activation')
        response = self.post('/api/auth/verify/', {'challengeId': response.json()['challengeId'], 'code': self.code()})
        self.assertEqual(response.json()['step'], 'login_required')
        user.refresh_from_db()
        self.assertEqual(user.email, 'legacy@example.com')
        self.assertTrue(AccountSecurity.objects.get(user=user).email_verified)

    def test_resend_invalidates_old_code(self):
        response = self.post('/api/auth/register/', {'username': 'alice', 'email': 'alice@example.com', 'password': self.password})
        old = self.code()
        challenge_id = response.json()['challengeId']
        self.assertEqual(self.post('/api/auth/resend/', {'challengeId': challenge_id}).status_code, 429)
        OtpChallenge.objects.filter(pk=challenge_id).update(last_sent_at=OtpChallenge.objects.get(pk=challenge_id).last_sent_at.replace(year=2020))
        self.assertEqual(self.post('/api/auth/resend/', {'challengeId': challenge_id}).status_code, 200)
        self.assertEqual(self.post('/api/auth/verify/', {'challengeId': challenge_id, 'code': old}).status_code, 400)

    def test_old_session_does_not_bypass_otp_and_disabled_legacy_stays_disabled(self):
        user = get_user_model().objects.create_user(username='legacy', password=self.password)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 404)
        self.client.logout()
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertEqual(self.post('/api/auth/login/', {'username': 'legacy', 'password': self.password}).status_code, 403)
        self.assertEqual(self.post('/api/auth/enroll-email/', {'email': 'legacy@example.com'}).status_code, 403)

    def test_wrong_codes_lock_login_for_ten_minutes(self):
        response = self.post('/api/auth/register/', {'username': 'alice', 'email': 'alice@example.com', 'password': self.password})
        challenge_id = response.json()['challengeId']
        correct = self.code()
        wrong = '000000' if correct != '000000' else '111111'
        for _ in range(5):
            self.assertEqual(self.post('/api/auth/verify/', {'challengeId': challenge_id, 'code': wrong}).status_code, 400)
        self.assertEqual(self.post('/api/auth/login/', {'username': 'alice', 'password': self.password}).status_code, 429)

    def test_profile_password_change_updates_login_password(self):
        response = self.post('/api/auth/register/', {'username': 'alice', 'email': 'alice@example.com', 'password': self.password})
        self.post('/api/auth/verify/', {'challengeId': response.json()['challengeId'], 'code': self.code()})
        response = self.post('/api/auth/login/', {'username': 'alice', 'password': self.password})
        self.post('/api/auth/verify/', {'challengeId': response.json()['challengeId'], 'code': self.code()})
        token = self.client.get('/api/auth/csrf/').json()['csrfToken']
        response = self.client.post('/api/auth/profile/', {'password': 'NewStrongPass456'}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 200)
        self.post('/api/auth/logout/', {})
        self.assertEqual(self.post('/api/auth/login/', {'username': 'alice', 'password': self.password}).status_code, 401)
        self.assertEqual(self.post('/api/auth/login/', {'username': 'alice', 'password': 'NewStrongPass456'}).status_code, 200)
