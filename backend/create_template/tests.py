import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.profiles import ensure_profile
from accounts.testing import verified_force_login
from .models import Criterion, Favorite, Item, Template


class DiscoverTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='author', password='test-password')
        self.author = ensure_profile(self.user)

    def test_empty_database_has_no_demo_templates(self):
        self.assertEqual(self.client.get('/api/templates/').json(), {'templates': []})

    def test_list_and_detail_return_database_content_and_viewer_favorites(self):
        template = Template.objects.create(owner=self.author, title='Real template', description='Database description')
        Criterion.objects.create(template=template, name='Quality', weight=3, order=0)
        Item.objects.create(template=template, name='Uploaded item', image='template_items/test.png', order=0)
        Favorite.objects.create(user=self.author, template=template)
        listing = self.client.get('/api/templates/').json()['templates']
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]['id'], template.pk)
        self.assertEqual(listing[0]['author']['name'], 'author')
        self.assertNotIn('email', listing[0]['author'])
        self.assertEqual(listing[0]['items'][0]['name'], 'Uploaded item')
        self.assertIn('/media/template_items/test.png', listing[0]['items'][0]['imageUrl'])
        self.assertEqual(listing[0]['popularity'], 1)
        self.assertFalse(listing[0]['isFavorite'])
        verified_force_login(self.client, self.user)
        detail = self.client.get(f'/api/templates/{template.pk}/').json()
        self.assertTrue(detail['isFavorite'])
        self.assertEqual(detail['criteria'][0]['weight'], 3)
        self.assertEqual(detail['description'], 'Database description')
        self.client.delete(f'/api/templates/{template.pk}/favorite/')
        detail = self.client.get(f'/api/templates/{template.pk}/').json()
        self.assertFalse(detail['isFavorite'])
        self.assertEqual(detail['popularity'], 0)
        self.client.post(f'/api/templates/{template.pk}/favorite/')
        self.assertTrue(self.client.get(f'/api/templates/{template.pk}/').json()['isFavorite'])
        self.author.userName = 'Updated author'
        self.author.save()
        self.assertEqual(self.client.get('/api/templates/').json()['templates'][0]['author']['name'], 'Updated author')

    def test_missing_template_returns_404(self):
        self.assertEqual(self.client.get('/api/templates/999999/').status_code, 404)

    def test_profile_hides_internal_email_placeholder(self):
        verified_force_login(self.client, self.user)
        profile = self.client.get('/api/auth/profile/').json()
        self.assertEqual(profile['userName'], 'author')
        self.assertEqual(profile['email'], '')

    def test_creation_rejects_non_integer_weights_without_creating_template(self):
        verified_force_login(self.client, self.user)
        for weight in (1.5, 1.0, '1.5', '2', True, None, 0, 11):
            with self.subTest(weight=weight):
                response = self.client.post('/api/templates/', {
                    'title': 'Invalid weight',
                    'criteria': json.dumps([{'name': 'Quality', 'weight': weight}]),
                    'items': json.dumps([{'name': 'Item'}]),
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn('权重', response.json()['detail'])
                self.assertEqual(Template.objects.count(), 0)
