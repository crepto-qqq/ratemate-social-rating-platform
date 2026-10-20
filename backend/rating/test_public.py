import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.profiles import ensure_profile
from accounts.testing import verified_force_login
from create_template.models import Template, Criterion, Item
from .views import _validate_scores
from .models import RatingResult, RatingScore, RatingResultLike, RatingResultComment


class PublicRatingTests(TestCase):
    def setUp(self):
        self.author_user = get_user_model().objects.create_user(username='author', password='test-password')
        self.viewer_user = get_user_model().objects.create_user(username='viewer', password='test-password')
        self.author = ensure_profile(self.author_user)
        self.viewer = ensure_profile(self.viewer_user)
        self.template = Template.objects.create(owner=self.author, title='Coffee ranking', description='A real comparison')
        self.criterion = Criterion.objects.create(template=self.template, name='Taste', weight=2)
        self.first = Item.objects.create(template=self.template, name='Espresso', image='test/espresso.png', order=0)
        self.second = Item.objects.create(template=self.template, name='Latte', image='test/latte.png', order=1)
        self.public = self.make_result(True)
        self.private = self.make_result(False)
        self.url = f'/api/ratings/public/{self.public.pk}/'

    def make_result(self, public, complete=True):
        result = RatingResult.objects.create(owner=self.author, template=self.template, is_public=public)
        RatingScore.objects.create(result=result, item=self.first, criterion=self.criterion, score=5)
        if complete:
            RatingScore.objects.create(result=result, item=self.second, criterion=self.criterion, score=3)
        return result

    def test_feed_only_exposes_complete_public_results(self):
        self.make_result(True, complete=False)
        response = self.client.get('/api/ratings/public/')
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual([r['id'] for r in results], [self.public.pk])
        self.assertEqual(results[0]['author']['name'], 'author')
        self.assertEqual(results[0]['ranking'][0]['score'], 100)
        self.assertIn('/media/test/espresso.png', results[0]['ranking'][0]['imageUrl'])
        self.assertNotIn('email', results[0]['author'])
        self.assertEqual(self.client.get(f'/api/ratings/public/{self.private.pk}/').status_code, 404)

    def test_search_and_pagination(self):
        self.assertEqual(len(self.client.get('/api/ratings/public/?q=Coffee').json()['results']), 1)
        self.assertEqual(self.client.get('/api/ratings/public/?q=missing').json()['results'], [])
        for _ in range(20):
            self.make_result(True)
        first = self.client.get('/api/ratings/public/').json()
        second = self.client.get('/api/ratings/public/?page=2').json()
        self.assertEqual(len(first['results']), 20)
        self.assertTrue(first['hasMore'])
        self.assertEqual(len(second['results']), 1)
        self.assertFalse(second['hasMore'])
        self.assertEqual(self.client.get('/api/ratings/public/?page=0').status_code, 400)

    def test_likes_are_unique_and_can_be_removed(self):
        verified_force_login(self.client, self.viewer_user)
        for _ in range(2):
            response = self.client.post(self.url + 'like/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'isLiked': True, 'likeCount': 1})
        self.assertEqual(RatingResultLike.objects.count(), 1)
        self.assertTrue(self.client.get(self.url).json()['isLiked'])
        self.assertEqual(self.client.get('/api/ratings/public/').json()['results'][0]['likeCount'], 1)
        response = self.client.delete(self.url + 'like/')
        self.assertEqual(response.json(), {'isLiked': False, 'likeCount': 0})

    def test_guest_and_self_likes_are_rejected(self):
        self.assertEqual(self.client.post(self.url + 'like/').status_code, 401)
        verified_force_login(self.client, self.author_user)
        self.assertTrue(self.client.get(self.url).json()['isOwner'])
        self.assertEqual(self.client.post(self.url + 'like/').status_code, 403)
        self.assertEqual(RatingResultLike.objects.count(), 0)

    def test_private_results_hide_interactions(self):
        verified_force_login(self.client, self.viewer_user)
        self.client.post(self.url + 'like/')
        self.public.is_public = False
        self.public.save(update_fields=['is_public'])
        for suffix in ('', 'comments/'):
            self.assertEqual(self.client.get(self.url + suffix).status_code, 404)
        self.assertEqual(self.client.post(self.url + 'like/').status_code, 404)
        self.assertEqual(self.client.get('/api/ratings/public/').json()['results'], [])

    def test_rating_creation_rechecks_template_after_validation(self):
        verified_force_login(self.client, self.viewer_user)
        baseline = RatingResult.objects.count()
        payload = {
            'templateId': self.template.pk,
            'isPublic': True,
            'scores': [
                {'itemId': item.pk, 'criterionId': self.criterion.pk, 'score': 4}
                for item in (self.first, self.second)
            ],
        }

        def hide_after_validation(template, scores):
            result = _validate_scores(template, scores)
            Template.objects.filter(pk=template.pk).update(is_hidden=True)
            return result

        with patch('rating.views._validate_scores', side_effect=hide_after_validation):
            response = self.client.post('/api/ratings/', json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(RatingResult.objects.count(), baseline)

    def test_result_comments_are_separate_and_manageable_by_author(self):
        verified_force_login(self.client, self.viewer_user)
        response = self.client.post(self.url + 'comments/', json.dumps({'content': 'Great ranking'}), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        comment_id = response.json()['id']
        self.assertEqual(self.template.comments.count(), 0)
        self.assertEqual(self.client.get(self.url).json()['commentCount'], 1)
        comment_url = self.url + f'comments/{comment_id}/'
        verified_force_login(self.client, self.author_user)
        self.assertEqual(self.client.delete(comment_url).status_code, 403)
        verified_force_login(self.client, self.viewer_user)
        response = self.client.patch(comment_url, json.dumps({'content': 'Edited comment'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['isEdited'])
        self.assertEqual(self.client.delete(comment_url).status_code, 204)
        self.assertEqual(RatingResultComment.objects.count(), 0)

    def test_comment_author_can_delete_after_template_is_hidden(self):
        verified_force_login(self.client, self.viewer_user)
        response = self.client.post(
            self.url + 'comments/', json.dumps({'content': 'Remove later'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        comment_url = self.url + f"comments/{response.json()['id']}/"
        self.template.is_hidden = True
        self.template.save(update_fields=['is_hidden'])

        self.assertEqual(
            self.client.patch(comment_url, json.dumps({'content': 'Edited'}),
                              content_type='application/json').status_code,
            404,
        )
        self.assertEqual(self.client.delete(comment_url).status_code, 204)
        self.assertFalse(RatingResultComment.objects.exists())

    def test_comment_validation_and_guest_permissions(self):
        self.assertEqual(self.client.post(self.url + 'comments/', '{}', content_type='application/json').status_code, 401)
        verified_force_login(self.client, self.viewer_user)
        for content in ('', ' ' * 3, 'x' * 2001):
            self.assertEqual(self.client.post(self.url + 'comments/', json.dumps({'content': content}), content_type='application/json').status_code, 400)

    def test_like_and_comment_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        verified_force_login(client, self.viewer_user)
        self.assertEqual(client.post(self.url + 'like/').status_code, 403)
        self.assertEqual(client.post(self.url + 'comments/', '{}', content_type='application/json').status_code, 403)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        self.assertEqual(client.post(self.url + 'like/', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.post(self.url + 'comments/', json.dumps({'content': 'CSRF protected'}), content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 201)
