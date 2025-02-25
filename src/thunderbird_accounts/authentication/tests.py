import base64
import uuid

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory
from rest_framework.test import RequestsClient

from django.contrib.auth import get_user_model

from thunderbird_accounts.authentication.const import GET_LOGIN_PATH, BAD_CREDENTIALS_MSG
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import handle_auth_callback_response
from thunderbird_accounts.client.models import Client, ClientEnvironment

from thunderbird_accounts.authentication.middleware import FXABackend, ClientSetAllowedHostsMiddleware


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


class FXABackendTestCase(TestCase):
    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get('/')
        self.backend = FXABackend()

        self.User = get_user_model()
        self.user = self.User.objects.create(fxa_id='abc123', email='user@test.com')

    def test_authenticate_with_matching_fxa_id(self):
        """Test authentication when fxa id matches existing user"""
        user = self.backend.authenticate(self.request, self.user.fxa_id, 'new@test.com')

        assert user
        self.assertEqual(user.uuid, self.user.uuid)
        self.assertEqual(user.fxa_id, self.user.fxa_id)

        # Confirm new email overwrites original when doing lookup by fxa id
        self.assertEqual(user.email, 'new@test.com')

    def test_authenticate_with_matching_email(self):
        """Test authentication when email matches existing user, but fxa id is new"""
        user = self.backend.authenticate(self.request, 'new_fxa_id', self.user.email)

        assert user
        self.assertEqual(user.uuid, self.user.uuid)
        self.assertEqual(user.email, self.user.email)

        # Confirm new fxa_id overwrites original when doing lookup by email
        self.assertEqual(user.fxa_id, 'new_fxa_id')

    def test_authenticate_with_no_match(self):
        """Test authentication with new user"""
        user = self.backend.authenticate(self.request, 'new_fxa_id', 'new@test.com')

        self.assertIsNone(user)

    def test_get_user_with_valid_id(self):
        user = self.backend.get_user(self.user.uuid)
        assert user
        self.assertIsNotNone(user.uuid)

    def test_get_user_with_invalid_id(self):
        bad_uuid = uuid.uuid4()
        user = self.backend.get_user(bad_uuid)
        self.assertIsNone(user)


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

        # Clear cache before each test
        cache.delete(settings.ALLOWED_HOSTS_CACHE_KEY)

    def tearDown(self):
        # Clean up cache after tests
        cache.delete(settings.ALLOWED_HOSTS_CACHE_KEY)

    def test_allowed_hosts_cache(self):
        """Test that middleware properly sets ALLOWED_HOSTS from ClientEnvironment"""
        self.middleware(self.request)
        self.assertIn('test.com', settings.ALLOWED_HOSTS)

    def test_allowed_uses_cached_hosts(self):
        """Test that middleware uses cached hosts when available"""
        cached_hosts = ['cached.com']
        cache.set(settings.ALLOWED_HOSTS_CACHE_KEY, cached_hosts)

        self.middleware(self.request)

        self.assertEqual(settings.ALLOWED_HOSTS, cached_hosts)
