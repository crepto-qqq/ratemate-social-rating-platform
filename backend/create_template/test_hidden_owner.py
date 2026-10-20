import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.profiles import ensure_profile
from accounts.testing import verified_force_login
from rating.models import RatingResult

from .models import Template


class HiddenContentStatusTests(TestCase):
    def test_only_affected_authors_see_hidden_status_and_reason(self):
        User = get_user_model()
        author = User.objects.create_user(username='template-author', password='password')
        rater = User.objects.create_user(username='rating-author', password='password')
        stranger = User.objects.create_user(username='stranger', password='password')
        admin = User.objects.create_user(username='moderator', password='password', is_staff=True)
        template_owner = ensure_profile(author)
        rating_owner = ensure_profile(rater)
        ensure_profile(stranger)
        template = Template.objects.create(owner=template_owner, title='Shared template')
        rating = RatingResult.objects.create(owner=rating_owner, template=template, is_public=True)

        verified_force_login(self.client, admin)
        response = self.client.post(
            f'/api/moderation/templates/{template.pk}/hide/',
            data=json.dumps({'reason': 'Contains prohibited material'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        verified_force_login(self.client, author)
        data = self.client.get('/api/templates/mine/hidden/').json()
        self.assertEqual(len(data['templates']), 1)
        self.assertEqual(data['templates'][0]['reason'], 'Contains prohibited material')
        self.assertEqual(data['ratings'], [])

        verified_force_login(self.client, rater)
        data = self.client.get('/api/templates/mine/hidden/').json()
        self.assertEqual(data['templates'], [])
        self.assertEqual(len(data['ratings']), 1)
        self.assertEqual(data['ratings'][0]['reason'], 'Contains prohibited material')
        self.assertTrue(self.client.get('/api/ratings/').json()['results'][0]['templateHidden'])
        self.assertEqual(self.client.patch(
            f'/api/ratings/{rating.pk}/', json.dumps({'isPublic': False}),
            content_type='application/json',
        ).status_code, 404)

        verified_force_login(self.client, stranger)
        self.assertEqual(self.client.get('/api/templates/mine/hidden/').json(), {
            'templates': [], 'ratings': [],
        })

        verified_force_login(self.client, admin)
        response = self.client.post(
            f'/api/moderation/templates/{template.pk}/restore/',
            data=json.dumps({'reason': 'Reviewed and approved'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        verified_force_login(self.client, rater)
        self.assertEqual(self.client.get('/api/templates/mine/hidden/').json()['ratings'], [])
