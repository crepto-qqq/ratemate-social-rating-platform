import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.profiles import ensure_profile
from create_template.models import Comment, Favorite, Template
from notifications.models import Notification
from rating.models import RatingResult, RatingResultComment, RatingResultLike

from .models import ModerationAction


class ModerationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(username='admin', password='password', is_staff=True)
        self.template_user = User.objects.create_user(username='template-owner', password='password')
        self.rating_user = User.objects.create_user(username='rating-owner', password='password')
        self.comment_user = User.objects.create_user(username='commenter', password='password')
        self.template_owner = ensure_profile(self.template_user)
        self.rating_owner = ensure_profile(self.rating_user)
        self.comment_author = ensure_profile(self.comment_user)
        self.template = Template.objects.create(owner=self.template_owner, title='Coffee list')
        self.rating = RatingResult.objects.create(owner=self.rating_owner, template=self.template, is_public=True)
        self.private_rating = RatingResult.objects.create(owner=self.rating_owner, template=self.template, is_public=False)
        self.favorite = Favorite.objects.create(user=self.comment_author, template=self.template)
        self.template_comment = Comment.objects.create(
            template=self.template, author=self.comment_author, content='Template comment body',
        )
        self.rating_comment = RatingResultComment.objects.create(
            result=self.rating, author=self.comment_author, content='Rating comment body',
        )
        self.client.force_login(self.admin_user)

    def post_reason(self, url, reason='Policy violation', client=None):
        return (client or self.client).post(
            url, json.dumps({'reason': reason}), content_type='application/json',
        )

    def test_staff_permissions_cover_reads_and_writes(self):
        urls = ('users/', 'templates/', 'ratings/', 'comments/', 'actions/')
        self.assertTrue(self.client.get('/api/moderation/me/').json()['isAdmin'])
        for url in urls:
            self.assertEqual(self.client.get('/api/moderation/' + url).status_code, 200)

        self.client.force_login(self.template_user)
        self.assertFalse(self.client.get('/api/moderation/me/').json()['isAdmin'])
        for url in urls:
            self.assertEqual(self.client.get('/api/moderation/' + url).status_code, 403)
        self.assertEqual(self.post_reason(f'/api/moderation/templates/{self.template.pk}/hide/').status_code, 403)
        self.client.logout()
        self.assertFalse(self.client.get('/api/moderation/me/').json()['isAdmin'])
        self.assertEqual(self.client.get('/api/moderation/templates/').status_code, 401)
        self.assertEqual(self.post_reason(f'/api/moderation/templates/{self.template.pk}/hide/').status_code, 401)

    def test_lists_search_content_and_exclude_private_ratings(self):
        users = self.client.get('/api/moderation/users/', {'q': 'rating-owner'}).json()['users']
        self.assertEqual([user['id'] for user in users], [self.rating_owner.pk])
        templates = self.client.get('/api/moderation/templates/', {'q': 'Coffee'}).json()['templates']
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]['ratingCount'], 1)
        self.assertEqual(templates[0]['favoriteCount'], 1)
        ratings = self.client.get('/api/moderation/ratings/').json()['ratings']
        self.assertEqual([rating['id'] for rating in ratings], [self.rating.pk])
        self.assertFalse(ratings[0]['templateHidden'])
        self.assertEqual(
            self.client.get(f'/api/moderation/templates/{self.template.pk}/').json()['template']['title'],
            'Coffee list',
        )
        self.assertEqual(
            self.client.get(f'/api/moderation/ratings/{self.rating.pk}/').json()['rating']['owner']['id'],
            self.rating_owner.pk,
        )
        self.assertEqual(self.client.get(f'/api/moderation/ratings/{self.private_rating.pk}/').status_code, 404)
        comments = self.client.get('/api/moderation/comments/').json()['comments']
        self.assertEqual({comment['kind'] for comment in comments}, {'template', 'rating'})
        rating_comments = self.client.get('/api/moderation/comments/', {'kind': 'rating'}).json()['comments']
        self.assertEqual([comment['id'] for comment in rating_comments], [self.rating_comment.pk])
        self.assertEqual(self.client.get('/api/moderation/comments/', {'kind': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get('/api/moderation/templates/', {'page': '0'}).status_code, 400)

    def test_hide_and_restore_keep_related_data_and_notify_affected_authors(self):
        hide_url = f'/api/moderation/templates/{self.template.pk}/hide/'
        response = self.post_reason(hide_url)
        self.assertEqual(response.status_code, 200)
        self.template.refresh_from_db()
        self.assertTrue(self.template.is_hidden)
        self.assertTrue(RatingResult.objects.filter(pk=self.rating.pk).exists())
        self.assertTrue(RatingResult.objects.filter(pk=self.private_rating.pk).exists())
        self.assertTrue(Favorite.objects.filter(pk=self.favorite.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.template_comment.pk).exists())
        notices = Notification.objects.filter(kind=Notification.MODERATION, action='hidden')
        self.assertEqual(set(notices.values_list('recipient_id', flat=True)),
                         {self.template_owner.pk, self.rating_owner.pk})
        self.assertEqual(self.post_reason(hide_url).status_code, 400)
        self.assertEqual(ModerationAction.objects.filter(action='hide_template').count(), 1)

        restore_url = f'/api/moderation/templates/{self.template.pk}/restore/'
        self.assertEqual(self.post_reason(restore_url, 'Appeal accepted').status_code, 200)
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_hidden)
        self.assertEqual(Notification.objects.filter(kind=Notification.MODERATION, action='restored').count(), 2)
        action = ModerationAction.objects.get(action='restore_template')
        self.assertEqual(action.actor, self.admin_user)
        self.assertEqual(action.reason, 'Appeal accepted')
        self.assertEqual(action.target_label, self.template.title)

    def test_hide_clears_old_interactions_but_keeps_moderation_history(self):
        Notification.objects.create(
            recipient=self.template_owner, kind=Notification.TEMPLATE_FAVORITE,
            target_type='template', target_id=self.template.pk, source_id=self.favorite.pk,
            summary=self.template.title,
        )
        like = RatingResultLike.objects.create(result=self.rating, user=self.comment_author)
        Notification.objects.create(
            recipient=self.rating_owner, kind=Notification.RATING_LIKE,
            target_type='rating', target_id=self.rating.pk, source_id=like.pk,
            summary=self.template.title,
        )
        self.post_reason(f'/api/moderation/templates/{self.template.pk}/hide/')
        self.assertEqual(Notification.objects.filter(kind__in=Notification.INTERACTION_KINDS).count(), 0)
        self.assertEqual(Notification.objects.filter(kind=Notification.MODERATION).count(), 2)

    def test_remove_public_rating_deletes_only_target_and_preserves_audit(self):
        url = f'/api/moderation/ratings/{self.rating.pk}/remove/'
        self.assertEqual(self.post_reason(url, '').status_code, 400)
        self.assertEqual(self.post_reason(url, 'x' * 1001).status_code, 400)
        self.assertEqual(ModerationAction.objects.count(), 0)
        self.assertEqual(self.post_reason(f'/api/moderation/ratings/{self.private_rating.pk}/remove/').status_code, 404)
        response = self.post_reason(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RatingResult.objects.filter(pk=self.rating.pk).exists())
        self.assertFalse(RatingResultComment.objects.filter(pk=self.rating_comment.pk).exists())
        self.assertTrue(RatingResult.objects.filter(pk=self.private_rating.pk).exists())
        self.assertTrue(Template.objects.filter(pk=self.template.pk).exists())
        action = ModerationAction.objects.get(action='remove_rating')
        self.assertEqual(action.target_id, self.rating.pk)
        self.assertEqual(action.reason, 'Policy violation')
        notice = Notification.objects.get(kind=Notification.MODERATION)
        self.assertEqual(notice.recipient, self.rating_owner)
        self.assertEqual(notice.action, 'removed')

    def test_remove_comment_notifies_only_comment_author(self):
        for kind, comment in (('template', self.template_comment), ('rating', self.rating_comment)):
            with self.subTest(kind=kind):
                source_kind = Notification.TEMPLATE_COMMENT if kind == 'template' else Notification.RATING_COMMENT
                target_type = 'template' if kind == 'template' else 'rating'
                target_id = self.template.pk if kind == 'template' else self.rating.pk
                Notification.objects.create(
                    recipient=self.template_owner, kind=source_kind, target_type=target_type,
                    target_id=target_id, source_id=comment.pk, summary=self.template.title,
                )
                url = f'/api/moderation/comments/{kind}/{comment.pk}/remove/'
                self.assertEqual(self.post_reason(url).status_code, 200)
                self.assertFalse(Notification.objects.filter(kind=source_kind, source_id=comment.pk).exists())
                notice = Notification.objects.filter(kind=Notification.MODERATION).last()
                self.assertEqual(notice.recipient, self.comment_author)
                self.assertNotIn('comment body', notice.summary.lower())
        self.assertEqual(ModerationAction.objects.filter(target_type='comment').count(), 2)

    def test_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_user)
        url = f'/api/moderation/templates/{self.template.pk}/hide/'
        self.assertEqual(self.post_reason(url, client=client).status_code, 403)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        response = client.post(
            url, json.dumps({'reason': 'Policy violation'}), content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
