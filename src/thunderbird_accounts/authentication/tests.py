from django.conf import settings
from django.http import HttpResponseRedirect
from django.test import TestCase
from rest_framework.test import RequestsClient

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import handle_auth_callback_response
from thunderbird_accounts.client.models import Client, ClientEnvironment


class APITestCase(TestCase):
    def setUp(self):
        self.GET_LOGIN_PATH = 'http://testserver/api/v1/auth/get-login/'
        self.BAD_CREDENTIALS_MSG = 'Authentication credentials were not provided.'

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
        response = self.factory.post(self.GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        self.assertEqual(response.status_code, 200)
        self.assertIn('login', response.json())

    def test_login_link_with_bad_host(self):
        self.client_env.allowed_hostnames = ['not-testserver']
        self.client_env.save()
        response = self.factory.post(self.GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        json_resp = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', json_resp)
        self.assertEqual(json_resp.get('detail'), self.BAD_CREDENTIALS_MSG)

    def test_login_link_with_bad_auth(self):
        self.client_env.auth_token = 'bad token bad token'

        response = self.factory.post(self.GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        json_resp = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', json_resp)
        self.assertEqual(json_resp.get('detail'), self.BAD_CREDENTIALS_MSG)

    def test_login_link_when_not_active(self):
        self.client_env.is_active = False
        self.client_env.save()

        response = self.factory.post(self.GET_LOGIN_PATH, {'secret': self.client_env.auth_token})
        json_resp = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', json_resp)
        self.assertEqual(json_resp.get('detail'), self.BAD_CREDENTIALS_MSG)


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
        client = Client.objects.create(name='Test Client')
        client_env = ClientEnvironment.objects.create(
            environment='test', redirect_url='https://www.thunderbird.net', client_id=client.uuid
        )

        response = handle_auth_callback_response(self.user, client_env)

        assert response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url.startswith(f'{client_env.redirect_url}?token=')

    def test_handle_auth_callback_response_with_admin(self):
        """Ensure this response does not have a token GET parameter"""
        response = handle_auth_callback_response(self.user, self.admin_client_env)

        assert response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == self.admin_client_env.redirect_url
        assert '?token=' not in response.url

    def test_handle_auth_callback_response_with_explicit_redirect_url(self):
        """Ensure this response does not have a token GET parameter because we're overriding the redirect_url"""
        redirect_url = 'https://addons.thunderbird.net'
        response = handle_auth_callback_response(self.user, self.admin_client_env, 'https://addons.thunderbird.net')

        assert response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url != self.admin_client_env.redirect_url
        assert response.url == redirect_url
        assert '?token=' not in response.url
