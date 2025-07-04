import base64

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory, Client as RequestClient
from django.urls import reverse
from rest_framework.test import RequestsClient


from thunderbird_accounts.authentication.const import GET_LOGIN_PATH, BAD_CREDENTIALS_MSG
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import (
    handle_auth_callback_response,
)
from thunderbird_accounts.client.models import Client, ClientEnvironment

from thunderbird_accounts.authentication.middleware import ClientSetAllowedHostsMiddleware


class APITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='Test',
            email='test@example.org',
        )

        self.factory = RequestsClient()

        self.client = Client.objects.create(name='Test Client')
        self.client_env = ClientEnvironment.objects.create(
            environment='test',
            redirect_url='http://testserver/',
            client_id=self.client.uuid,
            auth_token='1234',
        )
        self.client_env.allowed_hostnames = ['testserver']
        self.client_env.save()

    def test_login_link_successfully(self):
        response = self.factory.post(GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        self.assertEqual(response.status_code, 200)
        self.assertIn('login', response.json())

    def test_login_link_with_bad_host(self):
        self.client_env.allowed_hostnames = ['not-testserver']
        self.client_env.save()
        response = self.factory.post(GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        json_resp = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', json_resp)
        self.assertEqual(json_resp.get('detail'), BAD_CREDENTIALS_MSG)

    def test_login_link_with_bad_auth(self):
        self.client_env.auth_token = 'bad token bad token'

        response = self.factory.post(GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        json_resp = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', json_resp)
        self.assertEqual(json_resp.get('detail'), BAD_CREDENTIALS_MSG)

    def test_login_link_when_not_active(self):
        self.client_env.is_active = False
        self.client_env.save()

        response = self.factory.post(GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        json_resp = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', json_resp)
        self.assertEqual(json_resp.get('detail'), BAD_CREDENTIALS_MSG)


# Create your tests here.
class UtilsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='Test',
            email='test@example.org',
        )
        admin_client: Client = Client.objects.get(name=settings.ADMIN_CLIENT_NAME)
        self.admin_client_env = admin_client.clientenvironment_set.first()

    def test_handle_auth_callback_response(self):
        """Ensure this response has a token GET parameter"""
        user_session_id = 'test-session-id'
        user_session_id_b64 = base64.urlsafe_b64encode(user_session_id.encode()).decode()
        client = Client.objects.create(name='Test Client')
        client_env = ClientEnvironment.objects.create(
            environment='test', redirect_url='https://www.thunderbird.net', client_id=client.uuid
        )

        response = handle_auth_callback_response(client_env, user_session_id=user_session_id)

        assert response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url.startswith(f'{client_env.redirect_url}?user_session_id={user_session_id_b64}')

    def test_handle_auth_callback_response_with_admin(self):
        """Ensure this response does not have a token GET parameter"""
        response = handle_auth_callback_response(self.admin_client_env)

        assert response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == self.admin_client_env.redirect_url
        assert '?token=' not in response.url

    def test_handle_auth_callback_response_with_explicit_redirect_url(self):
        """Ensure this response does not have a token GET parameter because we're overriding the redirect_url"""
        redirect_url = 'https://addons.thunderbird.net'
        response = handle_auth_callback_response(self.admin_client_env, 'https://addons.thunderbird.net')

        assert response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url != self.admin_client_env.redirect_url
        assert response.url == redirect_url
        assert '?token=' not in response.url


class ClientSetAllowedHostsMiddlewareTestCase(TestCase):
    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get('/')
        self.middleware = ClientSetAllowedHostsMiddleware(get_response=lambda request: None)

        self.client = Client.objects.create(name='Test Client')
        self.client_env = ClientEnvironment.objects.create(
            environment='test',
            redirect_url='http://testserver/',
            client_id=self.client.uuid,
            auth_token='1234',
            allowed_hostnames=['test.com'],
        )

        self._original_allowed_hosts = settings.ALLOWED_HOSTS
        self._original_allowed_origins = settings.CORS_ALLOWED_ORIGINS

        # Clear cache before each test
        cache.delete(settings.ALLOWED_HOSTS_CACHE_KEY)
        cache.delete(settings.ALLOWED_ORIGINS_CACHE_KEY)

    def tearDown(self):
        # Clean up cache after tests
        cache.delete(settings.ALLOWED_HOSTS_CACHE_KEY)
        cache.delete(settings.ALLOWED_ORIGINS_CACHE_KEY)
        settings.ALLOWED_HOSTS = self._original_allowed_hosts
        settings.CORS_ALLOWED_ORIGINS = self._original_allowed_origins

    def test_allowed_hosts_cache(self):
        """Test that middleware properly sets ALLOWED_HOSTS from ClientEnvironment"""
        self.middleware(self.request)
        self.assertIn('test.com', settings.ALLOWED_HOSTS)
        self.assertIn('http://test.com', settings.CORS_ALLOWED_ORIGINS)

    def test_allowed_hosts_uses_cached_hosts(self):
        """Test that middleware uses cached hosts when available"""

        # Note: At this point there's no cache entry, so the allowed host cache is remade.
        cached_hosts = 'cached.com'
        settings.ALLOWED_HOSTS += [cached_hosts]

        self.middleware(self.request)

        self.assertIn(cached_hosts, settings.ALLOWED_HOSTS)
        self.assertNotIn(cached_hosts, settings.CORS_ALLOWED_ORIGINS)

    def test_allowed_origins_cached_hosts(self):
        """Test that middleware uses cached hosts when available"""

        # Note: At this point there's no cache entry, so the allowed host cache is remade.
        cached_hosts = 'https://cached.com'
        settings.CORS_ALLOWED_ORIGINS += [cached_hosts]

        self.middleware(self.request)

        self.assertNotIn(cached_hosts, settings.ALLOWED_HOSTS)
        self.assertIn(cached_hosts, settings.CORS_ALLOWED_ORIGINS)

    def test_both_cached_hosts(self):
        """Test that middleware uses cached hosts when available"""

        # Note: At this point there's no cache entry, so the allowed host cache is remade.
        cached_hosts = 'cached.com'
        cached_origins = f'https://{cached_hosts}'
        settings.ALLOWED_HOSTS += [cached_hosts]
        settings.CORS_ALLOWED_ORIGINS += [cached_origins]

        self.middleware(self.request)

        self.assertIn(cached_hosts, settings.ALLOWED_HOSTS)
        self.assertIn(cached_origins, settings.CORS_ALLOWED_ORIGINS)

    def test_allowed_origins_only_ingests_url_not_path(self):
        """Test that middleware uses cached hosts when available"""

        # Note: At this point there's no cache entry, so the allowed host cache is remade.
        ClientEnvironment.objects.create(
            environment='test',
            redirect_url='http://testserver2/really-long-url-holy-carp/whatever/',
            client_id=self.client.uuid,
            auth_token='12345',
            allowed_hostnames=['testserver2'],
        )

        self.middleware(self.request)

        self.assertIn('testserver2', settings.ALLOWED_HOSTS)
        self.assertIn('http://testserver2', settings.CORS_ALLOWED_ORIGINS)

    def test_allowed_origins_works_with_localhost(self):
        """Test that middleware uses cached hosts when available"""

        # Note: At this point there's no cache entry, so the allowed host cache is remade.
        ClientEnvironment.objects.create(
            environment='test',
            redirect_url='http://localhost:8080/really-long-url-holy-carp/whatever/',
            client_id=self.client.uuid,
            auth_token='12345',
            allowed_hostnames=['localhost:8080'],
        )

        self.middleware(self.request)

        self.assertIn('localhost:8080', settings.ALLOWED_HOSTS)
        self.assertIn('http://localhost:8080', settings.CORS_ALLOWED_ORIGINS)


class LoginRequiredTestCase(TestCase):
    # (URL reverse key, expected response status code),
    login_required_keys = [
        ('self_serve_home', 302),  # This one is a redirect
        ('self_serve_account_info', 200),
        ('self_serve_app_password', 200),
        ('self_serve_connection_info', 200),
        ('self_serve_subscription', 200),
        ('self_serve_subscription_success', 200),
    ]

    def test_logged_out(self):
        client = RequestClient()
        login_url = reverse(settings.LOGIN_URL)

        for key, _ in self.login_required_keys:
            url = reverse(key)
            self.assertTrue(url)

            response = client.get(url, follow=False)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(login_url))

    def test_logged_in(self):
        client = RequestClient()
        user = User.objects.get_or_create(username='test', oidc_id='1234')[0]
        client.force_login(user)

        for key, status in self.login_required_keys:
            url = reverse(key)
            self.assertTrue(url)

            response = client.get(url, follow=False)
            self.assertEqual(response.status_code, status)
            self.assertTrue(response.request['PATH_INFO'].startswith(url))
