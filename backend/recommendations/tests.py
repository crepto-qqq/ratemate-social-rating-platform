import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.profiles import ensure_profile
from create_template.models import Template, Criterion, Item, Favorite
from rating.models import RatingResult, RatingScore, RatingResultLike
from .embedding import MODEL
from .models import TemplateEmbedding, UserPreference
from .service import interest_weights
from .management.commands.embed_templates import process_next


def axis(index):
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


class RecommendationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='viewer', password='test-password')
        self.other_user = get_user_model().objects.create_user(username='author', password='test-password')
        self.viewer = ensure_profile(self.user)
        self.author = ensure_profile(self.other_user)
        self.client.force_login(self.user)
        self.coffee = self.template('Coffee and cafes', 0)
        self.similar = self.template('Espresso tasting', 0)
        self.unrelated = self.template('Camera equipment', 1)

    def template(self, title, vector_axis=0, owner=None):
        template = Template.objects.create(owner=owner or self.author, title=title)
        criterion = Criterion.objects.create(template=template, name='Quality', weight=1)
        item = Item.objects.create(template=template, name=title, image='test/item.png')
        TemplateEmbedding.objects.filter(template=template).update(
            status='ready', vector=axis(vector_axis), model=MODEL, content_hash=title, updated_at=timezone.now())
        return template

    def result(self, template, owner=None, public=True):
        result = RatingResult.objects.create(template=template, owner=owner or self.author, is_public=public)
        RatingScore.objects.create(result=result, item=template.items.first(), criterion=template.criteria.first(), score=5)
        return result

    def test_creation_auto_favorite_is_not_counted_twice(self):
        own = self.template('My own template', owner=self.viewer)
        Favorite.objects.create(template=own, user=self.viewer)
        self.assertEqual(interest_weights(self.viewer)[own.pk], 1)

    def test_combined_feedback_is_capped_per_template(self):
        Favorite.objects.create(template=self.coffee, user=self.viewer)
        self.result(self.coffee, owner=self.viewer)
        self.result(self.coffee, owner=self.viewer)
        first = self.result(self.coffee)
        second = self.result(self.coffee)
        RatingResultLike.objects.create(result=first, user=self.viewer)
        RatingResultLike.objects.create(result=second, user=self.viewer)
        self.assertEqual(interest_weights(self.viewer)[self.coffee.pk], 3)
        first.is_public = False
        second.is_public = False
        first.save(); second.save()
        self.assertEqual(interest_weights(self.viewer)[self.coffee.pk], 2)

    def test_similar_templates_rank_above_unrelated(self):
        Favorite.objects.create(template=self.coffee, user=self.viewer)
        data = self.client.get('/api/recommendations/?kind=templates').json()
        self.assertTrue(data['personalized'])
        ids = [t['id'] for t in data['templates']]
        self.assertLess(ids.index(self.similar.pk), ids.index(self.unrelated.pk))
        self.assertEqual(data['templates'][0]['recommendationReason'], 'Based on your interests')

    def test_unfavorite_rebuilds_preference_and_session_cache(self):
        favorite = Favorite.objects.create(template=self.coffee, user=self.viewer)
        self.client.get('/api/recommendations/?kind=templates')
        old_key = self.client.session['discover_recommendations_templates']['key']
        favorite.delete()
        data = self.client.get('/api/recommendations/?kind=templates').json()
        self.assertFalse(data['personalized'])
        self.assertNotEqual(old_key, self.client.session['discover_recommendations_templates']['key'])
        self.assertIsNone(UserPreference.objects.get(user=self.viewer).vector)

    def test_private_completed_ratings_only_inform_their_owner(self):
        private = self.result(self.coffee, owner=self.viewer, public=False)
        self.result(self.similar)
        self.result(self.unrelated)
        data = self.client.get('/api/recommendations/?kind=ratings').json()
        self.assertTrue(data['personalized'])
        self.assertNotIn(private.pk, [r['id'] for r in data['results']])
        self.assertEqual(data['results'][0]['template']['id'], self.similar.pk)
        self.client.logout()
        self.assertFalse(self.client.get('/api/recommendations/?kind=ratings').json()['personalized'])

    def test_unlike_changes_preference_and_seen_results(self):
        result = self.result(self.coffee)
        like = RatingResultLike.objects.create(result=result, user=self.viewer)
        data = self.client.get('/api/recommendations/?kind=ratings').json()
        self.assertEqual(data['results'], [])
        self.assertEqual(interest_weights(self.viewer)[self.coffee.pk], 3)
        like.delete()
        data = self.client.get('/api/recommendations/?kind=ratings').json()
        self.assertEqual(data['results'][0]['id'], result.pk)
        self.assertEqual(interest_weights(self.viewer), {})

    def test_two_results_across_all_like_combinations(self):
        first = self.result(self.coffee)
        second = self.result(self.unrelated)
        endpoint = '/api/recommendations/?kind=ratings'
        def returned_ids():
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            return {entry['id'] for entry in response.json()['results']}
        self.assertEqual(returned_ids(), {first.pk, second.pk})
        first_like = RatingResultLike.objects.create(result=first, user=self.viewer)
        self.assertEqual(returned_ids(), {second.pk})
        second_like = RatingResultLike.objects.create(result=second, user=self.viewer)
        self.assertEqual(returned_ids(), set())
        first_like.delete()
        self.assertEqual(returned_ids(), {first.pk})
        second_like.delete()
        self.assertEqual(returned_ids(), {first.pk, second.pk})

    def test_private_results_are_removed_even_after_cache(self):
        result = self.result(self.coffee)
        self.assertEqual(len(self.client.get('/api/recommendations/?kind=ratings').json()['results']), 1)
        result.is_public = False
        result.save(update_fields=['is_public'])
        self.assertEqual(self.client.get('/api/recommendations/?kind=ratings').json()['results'], [])

    def test_cold_start_ignores_creator_auto_favorites_for_heat(self):
        Favorite.objects.create(template=self.unrelated, user=self.author)
        Favorite.objects.create(template=self.similar, user=self.viewer)
        self.client.logout()
        data = self.client.get('/api/recommendations/?kind=templates').json()
        self.assertFalse(data['personalized'])
        self.assertEqual(data['templates'][0]['id'], self.similar.pk)

    def test_session_cache_reuses_order_and_has_bounded_age(self):
        Favorite.objects.create(template=self.coffee, user=self.viewer)
        first = self.client.get('/api/recommendations/?kind=templates').json()
        with patch('recommendations.service.CosineDistance', side_effect=AssertionError('Cache miss')):
            second = self.client.get('/api/recommendations/?kind=templates').json()
        self.assertEqual(first, second)
        session = self.client.session
        entry = session['discover_recommendations_templates']
        entry['generated'] -= 601
        session['discover_recommendations_templates'] = entry
        session.save()
        with patch('recommendations.service.CosineDistance', wraps=__import__('pgvector.django', fromlist=['CosineDistance']).CosineDistance) as distance:
            self.client.get('/api/recommendations/?kind=templates')
            self.assertTrue(distance.called)

    def test_template_changes_queue_new_embeddings(self):
        self.coffee.description = 'Updated content'
        self.coffee.save()
        embedding = TemplateEmbedding.objects.get(template=self.coffee)
        self.assertEqual(embedding.status, 'pending')
        self.assertIsNone(embedding.vector)

    def test_template_deletion_does_not_recreate_embedding(self):
        template_id = self.coffee.pk
        self.coffee.delete()
        self.assertFalse(TemplateEmbedding.objects.filter(template_id=template_id).exists())

    def test_candidate_deletion_refreshes_cached_ids(self):
        self.client.get('/api/recommendations/?kind=templates')
        deleted_id = self.unrelated.pk
        self.unrelated.delete()
        response = self.client.get('/api/recommendations/?kind=templates').json()
        self.assertNotIn(deleted_id, [template['id'] for template in response['templates']])

    def test_worker_failure_is_retryable_and_creation_remains_saved(self):
        self.coffee.save()
        with patch('recommendations.management.commands.embed_templates.embed_text', side_effect=RuntimeError('Offline')):
            self.assertTrue(process_next())
        embedding = TemplateEmbedding.objects.get(template=self.coffee)
        self.assertEqual(embedding.status, 'error')
        self.assertGreater(embedding.retry_at, timezone.now())
        self.assertTrue(Template.objects.filter(pk=self.coffee.pk).exists())

    def test_worker_will_not_publish_outdated_vectors(self):
        self.coffee.save()
        def changed(text):
            self.coffee.title = 'Changed during encoding'
            self.coffee.save()
            return axis(0)
        with patch('recommendations.management.commands.embed_templates.embed_text', side_effect=changed):
            process_next()
        embedding = TemplateEmbedding.objects.get(template=self.coffee)
        self.assertEqual(embedding.status, 'pending')
        self.assertIsNone(embedding.vector)

    def test_invalid_request_is_rejected(self):
        for query in ('kind=invalid', 'page=0', 'page=-1'):
            self.assertEqual(self.client.get('/api/recommendations/?' + query).status_code, 400)
