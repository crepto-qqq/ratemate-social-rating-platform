import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.profiles import ensure_profile
from create_template.models import Comment, Criterion, Favorite, Item, Template
from rating.models import RatingResult, RatingResultComment, RatingResultLike, RatingScore

from .models import Notification
from .services import notify_moderation


class NotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner_user = User.objects.create_user(username='owner', password='test-password')
        self.actor_user = User.objects.create_user(username='actor', password='test-password')
        self.stranger_user = User.objects.create_user(username='stranger', password='test-password')
        self.owner = ensure_profile(self.owner_user)
        self.actor = ensure_profile(self.actor_user)
        self.stranger = ensure_profile(self.stranger_user)
        self.template = Template.objects.create(owner=self.owner, title='Coffee')
        self.criterion = Criterion.objects.create(template=self.template, name='Taste', weight=1)
        self.item = Item.objects.create(template=self.template, name='Latte', image='test/latte.png')
        self.result = RatingResult.objects.create(owner=self.owner, template=self.template, is_public=True)
        RatingScore.objects.create(result=self.result, criterion=self.criterion, item=self.item, score=5)
        self.client.force_login(self.actor_user)

    def _comment(self, url, content):
        return self.client.post(url, json.dumps({'content': content}), content_type='application/json')

    def _notifications(self):
        self.client.force_login(self.owner_user)
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        return response.json()['notifications']

    def test_template_favorite_is_unique_self_excluded_and_undo_removes_notice(self):
        url = f'/api/templates/{self.template.pk}/favorite/'
        self.assertEqual(self.client.post(url).status_code, 201)
        self.assertEqual(self.client.post(url).status_code, 200)
        notice = self._notifications()
        self.assertEqual(len(notice), 1)
        self.assertEqual(notice[0]['type'], Notification.TEMPLATE_FAVORITE)
        self.assertEqual(notice[0]['actorName'], 'actor')
        self.assertEqual(notice[0]['targetUrl'], f'/templates/{self.template.pk}')
        self.assertEqual(self.client.post(url).status_code, 201)
        self.assertEqual(Notification.objects.count(), 1)  # Self favorite sends nothing.
        self.client.force_login(self.actor_user)
        self.assertEqual(self.client.delete(url).status_code, 200)
        self.assertEqual(Notification.objects.count(), 0)
        self.client.post(url)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Favorite.objects.filter(user=self.actor).count(), 1)

    def test_comment_preview_updates_then_disappears_on_delete(self):
        url = f'/api/templates/{self.template.pk}/comments/'
        response = self._comment(url, 'Nice template')
        self.assertEqual(response.status_code, 201)
        comment_url = f"{url}{response.json()['id']}/"
        self.assertEqual(self._notifications()[0]['preview'], 'Nice template')
        self.client.force_login(self.actor_user)
        self.assertEqual(self.client.patch(comment_url, json.dumps({'content': 'Better text'}), content_type='application/json').status_code, 200)
        self.assertEqual(self._notifications()[0]['preview'], 'Better text')
        self.client.force_login(self.actor_user)
        self.assertEqual(self.client.delete(comment_url).status_code, 204)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_rating_like_and_comment_follow_privacy_and_deletion(self):
        base = f'/api/ratings/public/{self.result.pk}/'
        self.client.post(base + 'like/')
        comment_id = self._comment(base + 'comments/', 'Great scores').json()['id']
        self.assertEqual(RatingResultLike.objects.count(), 1)
        self.assertEqual(RatingResultComment.objects.count(), 1)
        self.assertEqual({n['type'] for n in self._notifications()}, {
            Notification.RATING_LIKE, Notification.RATING_COMMENT,
        })
        self.client.force_login(self.actor_user)
        self.client.patch(base + f'comments/{comment_id}/', json.dumps({'content': 'Updated'}), content_type='application/json')
        self.assertEqual(Notification.objects.get(kind=Notification.RATING_COMMENT).preview, 'Updated')
        self.client.force_login(self.owner_user)
        self.assertEqual(self.client.patch(
            f'/api/ratings/{self.result.pk}/', json.dumps({'isPublic': False}),
            content_type='application/json',
        ).status_code, 200)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(RatingResultLike.objects.count(), 1)
        self.assertEqual(RatingResultComment.objects.count(), 1)
        self.client.patch(
            f'/api/ratings/{self.result.pk}/', json.dumps({'isPublic': True}),
            content_type='application/json',
        )
        self.assertEqual(Notification.objects.count(), 0)  # No historic backfill.
        self.client.force_login(self.actor_user)
        self._comment(base + 'comments/', 'New comment')
        self.assertEqual(Notification.objects.count(), 1)
        self.client.force_login(self.owner_user)
        self.client.delete(f'/api/ratings/{self.result.pk}/')
        self.assertEqual(Notification.objects.count(), 0)

    def test_hidden_template_cannot_receive_new_interactions_and_has_no_links(self):
        self.client.post(f'/api/templates/{self.template.pk}/favorite/')
        self.template.is_hidden = True
        self.template.save(update_fields=['is_hidden'])
        self.assertEqual(self._notifications()[0]['targetUrl'], '')
        self.client.force_login(self.actor_user)
        self.assertEqual(self.client.post(f'/api/templates/{self.template.pk}/favorite/').status_code, 404)
        self.assertEqual(self._comment(f'/api/templates/{self.template.pk}/comments/', 'hidden').status_code, 404)
        self.assertEqual(self.client.get(f'/api/ratings/public/{self.result.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/ratings/public/{self.result.pk}/like/').status_code, 404)

    def test_recipient_only_read_and_moderation_snapshot(self):
        notify_moderation(self.owner, 'removed', 'rating', self.result.pk, 'Coffee', 'Rule violation')
        self.assertEqual(self.client.get('/api/notifications/').json()['notifications'], [])
        self.assertEqual(self.client.get('/api/notifications/unread-count/').json()['unreadCount'], 0)
        self.client.force_login(self.owner_user)
        notice = self.client.get('/api/notifications/').json()['notifications'][0]
        self.assertEqual(notice['reason'], 'Rule violation')
        self.assertEqual(notice['targetUrl'], '')
        self.assertEqual(notice['actorName'], '')
        self.assertNotIn('admin', str(notice))
        self.client.force_login(self.stranger_user)
        self.assertEqual(self.client.post(f"/api/notifications/{notice['id']}/read/").status_code, 404)
        self.client.force_login(self.owner_user)
        self.assertEqual(self.client.post(f"/api/notifications/{notice['id']}/read/").json()['unreadCount'], 0)
        self.assertTrue(self.client.get('/api/notifications/').json()['notifications'][0]['isRead'])
        notify_moderation(self.owner, 'hidden', 'template', self.template.pk, 'Coffee', 'Second reason')
        self.assertEqual(self.client.get('/api/notifications/unread-count/').json()['unreadCount'], 1)
        self.assertEqual(self.client.post('/api/notifications/read-all/').json()['unreadCount'], 0)
        self.assertEqual(self.client.get('/api/notifications/unread-count/').json()['unreadCount'], 0)

    def test_auth_required_and_pagination_validation(self):
        self.client.logout()
        for url in ('/api/notifications/', '/api/notifications/unread-count/'):
            self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.post('/api/notifications/read-all/').status_code, 401)
        self.client.force_login(self.owner_user)
        for page in ('0', '-1', 'abc', '9999999'):
            self.assertEqual(self.client.get('/api/notifications/', {'page': page}).status_code, 400)

    def test_feed_is_newest_first_and_paginated(self):
        ids = [
            notify_moderation(self.owner, 'restored', 'template', self.template.pk,
                              f'Notice {index}', 'Resolved').pk
            for index in range(21)
        ]
        self.client.force_login(self.owner_user)
        first = self.client.get('/api/notifications/').json()
        second = self.client.get('/api/notifications/', {'page': 2}).json()
        self.assertEqual([notice['id'] for notice in first['notifications']], ids[:0:-1])
        self.assertTrue(first['hasMore'])
        self.assertEqual([notice['id'] for notice in second['notifications']], ids[:1])
        self.assertFalse(second['hasMore'])
        self.assertEqual(first['unreadCount'], 21)

    def test_unread_filter_paginates_unread_not_all_messages(self):
        older = notify_moderation(self.owner, 'hidden', 'template', self.template.pk, 'Older', 'Reason')
        for index in range(20):
            notice = notify_moderation(self.owner, 'restored', 'template', self.template.pk,
                                       f'Read {index}', 'Reason')
            notice.read_at = notice.created_at
            notice.save(update_fields=['read_at'])
        self.client.force_login(self.owner_user)
        feed = self.client.get('/api/notifications/', {'unread': '1'}).json()
        self.assertEqual([item['id'] for item in feed['notifications']], [older.pk])
        self.assertFalse(feed['hasMore'])
        self.assertEqual(feed['unreadCount'], 1)
        self.assertEqual(self.client.get('/api/notifications/', {'unread': 'yes'}).status_code, 400)
