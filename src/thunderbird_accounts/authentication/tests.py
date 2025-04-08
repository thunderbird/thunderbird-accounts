import base64
import datetime
import uuid
from unittest.mock import patch, Mock

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory
from django.test.utils import freeze_time
from rest_framework.test import RequestsClient, APIClient, APITestCase as DRF_APITestCase

from django.contrib.auth import get_user_model

from thunderbird_accounts.authentication.const import GET_LOGIN_PATH, BAD_CREDENTIALS_MSG
from thunderbird_accounts.authentication.models import User, UserSession
from thunderbird_accounts.authentication.utils import (
    handle_auth_callback_response,
    save_cache_session,
    get_cache_session,
    get_cache_allow_list_entry,
)
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
        cached_hosts = 'cached.com'
        settings.ALLOWED_HOSTS += [cached_hosts]

        self.middleware(self.request)

        self.assertIn(cached_hosts, settings.ALLOWED_HOSTS)


class FXAWebhooksTestCase(DRF_APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='Test', email='test@example.org', fxa_id='abc-123')

        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        # Clean up cache after tests
        cache.clear()

    def _webhook_call(self, assert_delete_called=False):
        with patch('thunderbird_accounts.client.tasks.send_notice_of_user_deletion', Mock()) as delete_task_mock:
            response = self.client.post('http://testserver/api/v1/auth/fxa/webhook')

            # Ensure the task wasn't called
            delete_task_mock.assert_not_called()
            (delete_task_mock.delay.assert_called_once()
             if assert_delete_called else delete_task_mock.delay.assert_not_called())
        return response

    def test_fxa_process_change_password(self):
        """Ensure the change password event is handled correctly"""
        self.client.force_authenticate(
            self.user,
            {
                'iss': 'https://accounts.firefox.com/',
                'sub': 'abc-123',
                'aud': 'REMOTE_SYSTEM',
                'iat': 1565720808,
                'jti': 'e19ed6c5-4816-4171-aa43-56ffe80dbda1',
                'events': {'https://schemas.accounts.firefox.com/event/password-change': {'changeTime': 1565721242227}},
            },
        )

        # Create a user session and save it in our cache
        user_session, created = UserSession.objects.update_or_create(user_id=self.user.uuid, session_key='abc123')
        save_cache_session(user_session)
        self.assertIsNotNone(get_cache_session(user_session.session_key))

        # Freeze time to before the changeTime timestamp and test the password change works correctly
        with freeze_time(datetime.datetime(year=2019, month=9, day=13).timestamp()):
            # Update the last login time to match our freeze_time
            self.user.last_login = datetime.datetime.now().astimezone(datetime.UTC)
            self.user.save()

            response = self._webhook_call(assert_delete_called=False)
            self.assertEqual(response.status_code, 200, response.content)

            user = User.objects.get(uuid=self.user.uuid)
            # Ensure our session cache no longer exists
            self.assertEqual(user.usersession_set.count(), 0)
            self.assertIsNone(get_cache_session(user_session.session_key))

        # Update the last login time to match our freeze_time
        self.user.last_login = datetime.datetime.now().astimezone(datetime.UTC)
        self.user.save()

        # Re-create the cache entry (aka re-login)
        save_cache_session(user_session)
        self.assertIsNotNone(get_cache_session(user_session.session_key))

        # Now we make sure an expired password change does not log us out.
        response = self._webhook_call(assert_delete_called=False)
        self.assertEqual(response.status_code, 200, response.content)

        # The request was outdated so we should still be logged in
        self.assertIsNotNone(get_cache_session(user_session.session_key))

    def test_fxa_process_change_primary_email(self):
        OLD_EMAIL = self.user.email
        NEW_EMAIL = 'john.butterfly@example.org'

        self.client.force_authenticate(
            self.user,
            {
                'iss': 'https://accounts.firefox.com/',
                'sub': 'abc-123',
                'aud': 'REMOTE_SYSTEM',
                'iat': 1565720808,
                'jti': 'e19ed6c5-4816-4171-aa43-56ffe80dbda1',
                'events': {'https://schemas.accounts.firefox.com/event/profile-change': {'email': NEW_EMAIL}},
            },
        )

        # Create a user session and save it in our cache
        user_session, created = UserSession.objects.update_or_create(user_id=self.user.uuid, session_key='abc123')
        save_cache_session(user_session)
        self.assertIsNotNone(get_cache_session(user_session.session_key))

        self.assertEqual(self.user.email, OLD_EMAIL)

        # Trigger the profile change event
        response = self._webhook_call(assert_delete_called=False)

        self.assertEqual(response.status_code, 200, response.content)

        user = User.objects.get(uuid=self.user.uuid)

        # We should be logged out
        self.assertIsNone(get_cache_session(user_session.session_key))

        # Ensure the email has changed
        self.assertNotEqual(user.email, OLD_EMAIL)
        self.assertEqual(user.email, NEW_EMAIL)

        # TODO: Profile updating? (this happens on login so not to concerned.)

    def test_fxa_process_delete_user(self):
        self.client.force_authenticate(
            self.user,
            {
                'iss': 'https://accounts.firefox.com/',
                'sub': 'abc-123',
                'aud': 'REMOTE_SYSTEM',
                'iat': 1565720810,
                'jti': '1b3d623a-300a-4ab8-9241-855c35586809',
                'events': {'https://schemas.accounts.firefox.com/event/delete-user': {}},
            },
        )

        # Create a user session and save it in our cache
        user_session, created = UserSession.objects.update_or_create(user_id=self.user.uuid, session_key='abc123')
        save_cache_session(user_session)
        self.assertIsNotNone(get_cache_session(user_session.session_key))

        # Trigger the delete user event
        response = self._webhook_call(assert_delete_called=True)

        self.assertEqual(response.status_code, 200, response.content)

        # We shouldn't exist anymore
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(uuid=self.user.uuid)

        # We should be logged out
        self.assertIsNone(get_cache_session(user_session.session_key))


class AllowListTestCase(DRF_APITestCase):
    def setUp(self):
        cache.clear()

        self.api_client = APIClient()
        self.user = User.objects.create(username='Test', email='test@example.org', fxa_id='abc-123')

        self.client = Client.objects.create(name='Test Client')
        self.client_env = ClientEnvironment.objects.create(
            environment='test',
            redirect_url='http://testserver/',
            client_id=self.client.uuid,
            auth_token='1234',
            is_public=False,  # Important, otherwise it'll always be yes
        )
        self.client_env.allowed_hostnames = ['testserver']
        self.client_env.save()

    def tearDown(self):
        cache.clear()

    def test_client_env_is_public(self):
        # Make the client env public
        self.client_env.is_public = True
        self.client_env.save()

        # Normally not in allow list!
        settings.FXA_ALLOW_LIST = '@example.net'
        email = 'greg@example.org'

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': email, 'secret': self.client_env.auth_token},
        )
        result = response.json().get('result')

        self.assertIsNotNone(result)
        self.assertTrue(result)

    def test_is_in_allow_list(self):
        settings.FXA_ALLOW_LIST = '@example.org'
        email = 'greg@example.org'

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': email, 'secret': self.client_env.auth_token},
        )
        result = response.json().get('result')

        self.assertIsNotNone(result)
        self.assertTrue(result)

    def test_is_a_user(self):
        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': self.user.email, 'secret': self.client_env.auth_token},
        )
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json().get('result')

        self.assertIsNotNone(result)
        self.assertTrue(result)

    def test_is_not_in_list(self):
        settings.FXA_ALLOW_LIST = '@example.org'
        email = 'greg@example.com'

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': email, 'secret': self.client_env.auth_token},
        )
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json().get('result')

        self.assertIsNotNone(result)
        self.assertFalse(result)

    def test_entry_is_cached(self):
        """Test that the entry is cached, and is deleted on user delete"""
        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': self.user.email, 'secret': self.client_env.auth_token},
        )
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json().get('result')

        self.assertIsNotNone(result)
        self.assertTrue(result)

        self.assertTrue(get_cache_allow_list_entry(self.user.email))

        # okay lets delete the user, this should remove the cache...
        self.user.delete()

        self.assertIsNone(self.user.uuid)

        self.assertFalse(get_cache_allow_list_entry(self.user.email))

    def test_entry_with_updated_email_is_uncached(self):
        """If a user's email changes via a fxa webhook, we should make sure the cache is cleared for that entry."""
        settings.FXA_ALLOW_LIST = '@example.com'  # Not .org like the original email!
        original_email = self.user.email
        new_email = 'new-email@example.com'

        # Wouldn't normally be in the allow list
        self.assertFalse(original_email.endswith(settings.FXA_ALLOW_LIST))

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': self.user.email, 'secret': self.client_env.auth_token},
        )
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json().get('result')

        self.assertIsNotNone(result)
        self.assertTrue(result)

        self.assertTrue(get_cache_allow_list_entry(self.user.email))

        # okay lets change the user's email, this should remove the cache
        self.user.email = new_email
        self.user.save()

        # The cache entry should be gone
        self.assertIsNone(get_cache_allow_list_entry(original_email))

        # Okay the allow list should return false now
        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': original_email, 'secret': self.client_env.auth_token},
        )
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json().get('result')
        self.assertIsNotNone(result)
        self.assertFalse(result)

    def test_with_no_allow_list(self):
        settings.FXA_ALLOW_LIST = ''
        emails = ['greg@example.org', self.user.email]

        while len(emails) > 0:
            email = emails.pop()
            response = self.api_client.post(
                'http://testserver/api/v1/auth/is-in-allow-list/',
                data={'email': email, 'secret': self.client_env.auth_token},
            )
            result = response.json().get('result')

            self.assertIsNotNone(result)
            self.assertTrue(result)

        # Make sure we've tested each email
        self.assertEqual(len(emails), 0)

    def test_with_no_email(self):
        settings.FXA_ALLOW_LIST = '@example.org'

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'secret': self.client_env.auth_token},
        )
        result = response.json()

        self.assertEqual(response.status_code, 400)
        # Ensure we have an email key in the json
        self.assertIn('email', result)

    def test_with_no_secret(self):
        settings.FXA_ALLOW_LIST = '@example.org'
        email = 'greg@example.org'

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={'email': email},
        )
        result = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', result)
        self.assertEqual(result['detail'], 'Authentication credentials were not provided.')

    def test_with_no_secret_or_email(self):
        settings.FXA_ALLOW_LIST = '@example.org'

        response = self.api_client.post(
            'http://testserver/api/v1/auth/is-in-allow-list/',
            data={},
        )
        result = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', result)
        self.assertEqual(result['detail'], 'Authentication credentials were not provided.')
