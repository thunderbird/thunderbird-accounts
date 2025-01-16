from django.conf import settings
from django.http import HttpResponseRedirect
from django.test import TestCase
from rest_framework.test import RequestsClient

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import handle_auth_callback_response
from thunderbird_accounts.client.models import Client, ClientEnvironment


class APITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='Test',
            email='test@example.org',
        )
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
        factory = RequestsClient()
        response = factory.post('http://testserver/api/v1/auth/get-login/', {'secret': self.client_env.auth_token})
        assert response.status_code == 200, response.status_code
        assert 'login' in response.json()

    def test_login_link_unsuccessful_bad_host(self):
        self.client_env.allowed_hostnames = ['not-testserver']
        self.client_env.save()
        factory = RequestsClient()
        response = factory.post('http://testserver/api/v1/auth/get-login/', {'secret': self.client_env.auth_token})
        json_resp = response.json()

        assert response.status_code == 401, response.status_code
        assert 'detail' in json_resp
        assert json_resp.get('detail') == 'Authentication credentials were not provided.'

    def test_login_link_unsuccessful_bad_auth(self):
        self.client_env.auth_token = 'bad token bad token'

        factory = RequestsClient()
        response = factory.post('http://testserver/api/v1/auth/get-login/', {'secret': self.client_env.auth_token})
        json_resp = response.json()

        assert response.status_code == 401, response.status_code
        assert 'detail' in json_resp
        assert json_resp.get('detail') == 'Authentication credentials were not provided.'

    def test_login_link_unsuccessful_not_active(self):
        self.client_env.is_active = False
        self.client_env.save()

        factory = RequestsClient()
        response = factory.post('http://testserver/api/v1/auth/get-login/', {'secret': self.client_env.auth_token})
        json_resp = response.json()

        assert response.status_code == 401, response.status_code
        assert json_resp.get('detail') == 'Authentication credentials were not provided.'


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
