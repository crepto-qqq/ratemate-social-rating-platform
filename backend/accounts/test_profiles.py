import json
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import User_profile
from create_template.models import Template


class AccountProfileTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def csrf(self):
        return self.client.get('/api/auth/csrf/').json()['csrfToken']

    def test_registration_login_and_template_creation(self):
        credentials = {'username': 'profile_test', 'password': 'test-password'}
        response = self.client.post('/api/auth/register/', json.dumps(credentials),
                                    content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='profile_test')
        self.assertTrue(User_profile.objects.filter(user=user).exists())
        response = self.client.post('/api/auth/login/', json.dumps(credentials),
                                    content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/auth/profile/').status_code, 200)
        image = BytesIO()
        Image.new('RGB', (2, 2)).save(image, format='PNG')
        response = self.client.post('/api/templates/', {
            'title': 'Test template',
            'criteria': json.dumps([{'name': 'Quality', 'weight': 1}]),
            'items': json.dumps([{'name': 'Item'}]),
            'item_image_0': SimpleUploadedFile('item.png', image.getvalue(), content_type='image/png'),
        }, HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 201, response.content)
        template = Template.objects.get(pk=response.json()['id'])
        self.assertEqual(template.owner.user_id, user.pk)
        response = self.client.get('/api/templates/favorites/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['templates']), 1)

    def test_existing_account_gets_profile_and_rename_keeps_link(self):
        user = get_user_model().objects.create_user(username='existing', password='test-password')
        self.client.force_login(user)
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, 200)
        profile_id = response.json()['id']
        response = self.client.post('/api/auth/profile/', {'userName': 'renamed'},
                                    HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/auth/profile/').json()['id'], profile_id)
        self.assertEqual(User_profile.objects.filter(user=user).count(), 1)
        self.assertEqual(self.client.get('/api/templates/favorites/').status_code, 200)

    def test_display_name_does_not_claim_unlinked_profile(self):
        legacy = User_profile.objects.create(userName='existing', email='legacy@example.com', password='unused')
        user = get_user_model().objects.create_user(username='existing', password='test-password')
        self.client.force_login(user)
        response = self.client.get('/api/auth/profile/')
        self.assertNotEqual(response.json()['id'], legacy.pk)
        legacy.refresh_from_db()
        self.assertIsNone(legacy.user_id)