from django.test import Client, SimpleTestCase


class CsrfTests(SimpleTestCase):
    def test_register_requires_cookie_and_matching_header(self):
        client = Client(enforce_csrf_checks=True)
        url = '/api/auth/register/'
        body = '{}'
        self.assertEqual(client.post(url, body, content_type='application/json').status_code, 403)
        response = client.get('/api/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)
        token = response.json()['csrfToken']
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(client.post(url, body, content_type='application/json').status_code, 403)
        self.assertEqual(client.post(url, body, content_type='application/json', HTTP_X_CSRFTOKEN='wrong').status_code, 403)
        # Invalid credentials yield the view's 400, proving CSRF passed without creating a user.
        response = client.post(url, body, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.json())

    def test_login_accepts_token_through_frontend_origin(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        response = client.post('/api/auth/login/', '{}', content_type='application/json',
                               HTTP_X_CSRFTOKEN=token, HTTP_HOST='localhost:5173',
                               HTTP_ORIGIN='http://localhost:5173')
        self.assertEqual(response.status_code, 400)