import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.profiles import ensure_profile
from .models import Template


class CommentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='commenter', password='test-password')
        self.other = get_user_model().objects.create_user(username='other', password='test-password')
        self.template = Template.objects.create(owner=ensure_profile(self.user), title='Comments template')
        self.url = f'/api/templates/{self.template.pk}/comments/'

    def post(self, content='Hello', client=None):
        return (client or self.client).post(self.url, json.dumps({'content': content}), content_type='application/json')

    def test_guest_reads_but_cannot_write(self):
        self.assertEqual(self.client.get(self.url).json(), {'comments': [], 'hasMore': False})
        self.assertEqual(self.post().status_code, 401)

    def test_persistence_author_details_edit_and_delete(self):
        self.client.force_login(self.user)
        response = self.post('  Hello\nworld  ')
        self.assertEqual(response.status_code, 201)
        comment = response.json()
        self.assertEqual(comment['content'], 'Hello\nworld')
        self.assertTrue(comment['canManage'])
        self.assertNotIn('email', comment['author'])
        detail_url = f"{self.url}{comment['id']}/"
        self.client.logout()
        listed = self.client.get(self.url).json()['comments'][0]
        self.assertFalse(listed['canManage'])
        self.assertEqual(listed['content'], 'Hello\nworld')
        self.assertEqual(self.client.patch(detail_url, json.dumps({'content': 'Edited'}), content_type='application/json').status_code, 401)
        self.client.force_login(self.other)
        self.assertEqual(self.client.patch(detail_url, json.dumps({'content': 'Edited'}), content_type='application/json').status_code, 403)
        self.assertEqual(self.client.delete(detail_url).status_code, 403)
        self.client.force_login(self.user)
        response = self.client.patch(detail_url, json.dumps({'content': 'Edited'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['content'], 'Edited')
        self.assertTrue(response.json()['isEdited'])
        self.assertEqual(self.client.delete(detail_url).status_code, 204)
        self.assertEqual(self.client.get(self.url).json()['comments'], [])

    def test_invalid_content_and_json(self):
        self.client.force_login(self.user)
        for content in ['', ' \n ', 'x' * 2001, None, 5]:
            with self.subTest(content=str(content)[:10]):
                self.assertEqual(self.post(content).status_code, 400)
        for body in ['{', '[]', '{}', 'null']:
            self.assertEqual(self.client.post(self.url, body, content_type='application/json').status_code, 400)
        self.assertEqual(self.post('x' * 2000).status_code, 201)

    def test_paginated_newest_first_and_validation(self):
        self.client.force_login(self.user)
        ids = [self.post(str(i)).json()['id'] for i in range(21)]
        page = self.client.get(self.url).json()
        self.assertEqual([c['id'] for c in page['comments']], ids[::-1][:20])
        self.assertTrue(page['hasMore'])
        page = self.client.get(self.url, {'page': 2}).json()
        self.assertEqual([c['id'] for c in page['comments']], ids[:1])
        self.assertFalse(page['hasMore'])
        for page in ['0', '-1', 'invalid', '1.5', '9' * 100]:
            self.assertEqual(self.client.get(self.url, {'page': page}).status_code, 400)

    def test_missing_and_cross_template_comments(self):
        self.assertEqual(self.client.get('/api/templates/999999/comments/').status_code, 404)
        self.client.force_login(self.user)
        comment_id = self.post().json()['id']
        other_template = Template.objects.create(owner=ensure_profile(self.user), title='Other')
        self.assertEqual(self.client.delete(f'/api/templates/{other_template.pk}/comments/{comment_id}/').status_code, 404)
        self.assertEqual(self.client.delete(self.url + '999999/').status_code, 404)

    def test_csrf_enforced_for_all_writes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(self.post(client=client).status_code, 403)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        created = client.post(self.url, json.dumps({'content': 'CSRF checked'}), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(created.status_code, 201)
        url = f"{self.url}{created.json()['id']}/"
        self.assertEqual(client.patch(url, json.dumps({'content': 'Changed'}), content_type='application/json').status_code, 403)
        self.assertEqual(client.delete(url).status_code, 403)
