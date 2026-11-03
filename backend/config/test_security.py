from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path


def private_error(request):
    raise RuntimeError('private-stack-marker')


def forbidden(request):
    raise PermissionDenied('private-permission-marker')


def invalid(request):
    raise SuspiciousOperation('private-request-marker')


urlpatterns = [path('explode/', private_error), path('forbidden/', forbidden), path('invalid/', invalid)]
handler400 = 'config.errors.bad_request'
handler403 = 'config.errors.permission_denied'
handler404 = 'config.errors.not_found'
handler500 = 'config.errors.server_error'


@override_settings(DEBUG=False, ROOT_URLCONF=__name__, ALLOWED_HOSTS=['testserver'])
class ProductionErrorTests(SimpleTestCase):
    def test_server_error_hides_traceback_and_exception_text(self):
        client = Client(raise_request_exception=False)
        with self.assertLogs('django.request', level='ERROR'):
            response = client.get('/explode/')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['detail'], 'An unexpected error occurred. Please try again later.')
        self.assertNotIn(b'private-stack-marker', response.content)
        self.assertNotIn(b'Traceback', response.content)

    def test_missing_resource_and_access_errors_are_generic_json(self):
        for url, status in [('/missing/', 404), ('/forbidden/', 403), ('/invalid/', 400)]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)
                self.assertIn('detail', response.json())
                self.assertNotIn(b'private-', response.content)

    @override_settings(ROOT_URLCONF='config.urls')
    def test_cross_origin_post_with_valid_token_is_still_rejected(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        response = client.post('/api/auth/login/', '{}', content_type='application/json',
                               HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN='https://untrusted.invalid', secure=True)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['detail'], 'Security verification failed. Refresh the page and try again.')
