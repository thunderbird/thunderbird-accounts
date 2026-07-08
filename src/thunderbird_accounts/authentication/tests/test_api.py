from thunderbird_accounts.core.tests.utils import oidc_force_login
from django.contrib.auth.models import Permission
from thunderbird_accounts.authentication.api import CanISignUpResponses
from django.urls import reverse
from json import JSONDecodeError
from unittest.mock import MagicMock, patch
from waffle.models import Flag
import uuid

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from urllib.parse import quote
from django.test import Client as RequestClient, override_settings
from rest_framework.test import APITestCase, APIClient

from thunderbird_accounts.authentication.exceptions import ImportUserError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.authentication.models import AllowListEntry


@override_settings(USE_ALLOW_LIST=True)
@patch('thunderbird_accounts.authentication.clients.KeycloakClient.import_user')
class SignUpTestcase(APITestCase):
    def setUp(self):
        self.client = RequestClient()
        self.wait_list = ['hello@example.com', 'hello2@example.com']
        for entry in self.wait_list:
            AllowListEntry.objects.create(email=entry)

    def get_messages(self, response):
        """Little helper message to retrieve flash messages"""
        try:
            resp = response.json()
            return f'[{resp.get("type", "unk-type")}]: {resp.get("error", "unknown error.")}'
        except JSONDecodeError:
            return 'Non-standard error returned.'

    def make_sign_up_data(self, *args, **kwargs) -> dict:
        """Factory for sign up data. Pass in kwargs to override any data you need."""
        return {
            'email': 'hello@example.com',
            'zoneinfo': 'UTC',
            'locale': 'en',
            'partialUsername': 'hello',
            'password': '123',
            **kwargs,
        }

    def test_success(self, mock_import_user: MagicMock):
        """Test that an unauthenticated user can sign-up if they're in the allow list."""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=self.wait_list[0]),
        )
        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 200, msg=assert_fail_msg)
        self.assertEqual(response.json(), {'success': True}, msg=assert_fail_msg)

    def test_success_with_zoneinfo_null(self, mock_import_user: MagicMock):
        """Test that an unauthenticated user can sign-up if they're in the allow list."""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        sign_up_data = self.make_sign_up_data(email=self.wait_list[0], zoneinfo='')

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            sign_up_data,
        )
        assert_fail_msg = self.get_messages(response)

        # Make sure the default value overrides the one we used during signup
        self.assertNotEqual(mock_import_user.call_args.kwargs['timezone'], sign_up_data.get('zoneinfo'))
        self.assertEqual(mock_import_user.call_args.kwargs['timezone'], 'UTC')

        self.assertEqual(response.status_code, 200, msg=assert_fail_msg)
        self.assertEqual(response.json(), {'success': True}, msg=assert_fail_msg)

    def test_not_on_allowed_list(self, mock_import_user: MagicMock):
        """Test that a recovery email not on the allow list will ship them to the wait list"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        mock_user_email = 'hello3@example.com'

        # Redirect should include mock user's email in querystring
        waitlist_url = f'{settings.TB_PRO_WAIT_LIST_URL}?email={quote(mock_user_email)}'

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=mock_user_email),
        )
        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 403, msg=assert_fail_msg)

        resp_data = response.json()
        self.assertEqual(resp_data.get('type'), 'go-to-wait-list', msg=assert_fail_msg)
        self.assertEqual(resp_data.get('href'), waitlist_url, msg=assert_fail_msg)

    def test_user_already_exists(self, mock_import_user: MagicMock):
        """Test that we check if a user exists before creating a user"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        User(email=self.wait_list[0], username='hello@example.org').save()

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=self.wait_list[0], partialUsername='hello'),
        )
        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 400, msg=assert_fail_msg)

        resp_data = response.json()
        self.assertEqual(resp_data.get('type'), 'username-in-use', msg=assert_fail_msg)

    def test_user_alias_already_exists(self, mock_import_user: MagicMock):
        """When signing up make sure we're not using a username on a shared domain"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        username = f'hello@{settings.PRIMARY_EMAIL_DOMAIN}'
        user = User.objects.create(email=self.wait_list[0], username=username)
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=f'hello2@{settings.ALLOWED_EMAIL_DOMAINS[1]}', account=account)

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=self.wait_list[0], partialUsername='hello2'),
        )
        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 400, msg=assert_fail_msg)

        resp_data = response.json()
        self.assertEqual(resp_data.get('type'), 'username-in-use', msg=assert_fail_msg)

    def test_user_using_reserved_emails(self, _mock_import_user: MagicMock):
        """Test to ensure that a user does not use a reserved username"""
        User(email=self.wait_list[0], username='hello@example.org').save()

        # All examples from reserved.py
        for local_part in ['thunderbird_admin', 'admin', 'postmaster', 'root']:
            response = self.client.post(
                '/api/v1/auth/sign-up/',
                self.make_sign_up_data(email=self.wait_list[0], partialUsername=local_part),
            )
            assert_fail_msg = self.get_messages(response)

            self.assertEqual(response.status_code, 400, msg=assert_fail_msg)

            resp_data = response.json()
            self.assertEqual(resp_data.get('type'), 'username-in-use', msg=assert_fail_msg)

    def test_alias_already_exists(self, mock_import_user: MagicMock):
        """Test that we check if a alias exists before creating a user"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        alias = 'not_in_examples'

        user = User(email='not_in_examples@example.org', username=f'{alias}@example.org').save()
        account = Account(name='{alias}@example.org', user=user).save()
        Email(address=self.wait_list[0], type=Email.EmailType.ALIAS, account=account).save()

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=self.wait_list[0], partialUsername=alias),
        )
        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 400, msg=assert_fail_msg)

        resp_data = response.json()
        self.assertEqual(resp_data.get('type'), 'username-in-use', msg=assert_fail_msg)

    def test_passwords_are_empty(self, mock_import_user: MagicMock):
        """Test that we check if passwords exist"""

        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=self.wait_list[0], password=''),
        )
        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 400, msg=assert_fail_msg)

        resp_data = response.json()
        self.assertEqual(resp_data.get('type'), 'password-is-empty', msg=assert_fail_msg)

    def test_import_errors_propagate(self, mock_import_user: MagicMock):
        """Test to make sure keycloak import user errors propagate to the frontend via messages"""
        mock_test_error = 'This is a test error.'
        mock_test_type = 'TEST'
        mock_import_user.side_effect = ImportUserError(
            'Test Error', username='hello', error_code=mock_test_type, error_desc=mock_test_error
        )
        response = self.client.post(
            '/api/v1/auth/sign-up/',
            self.make_sign_up_data(email=self.wait_list[0]),
        )

        assert_fail_msg = self.get_messages(response)

        self.assertEqual(response.status_code, 400, msg=assert_fail_msg)

        resp_data = response.json()
        self.assertEqual(resp_data.get('type'), mock_test_type, msg=assert_fail_msg)
        self.assertEqual(resp_data.get('error'), mock_test_error, msg=assert_fail_msg)


@override_settings(USE_ALLOW_LIST=True)
class CanISignUpTestcase(APITestCase):
    def setUp(self):
        self.client = RequestClient()

        self.wait_list = [
            '348b8787-ddf0-4ab9-931e-db388f8770c0@example.com',
            '153ff958-dabb-4afc-94ab-3b1b3b5ff051@example.com',
            '23fd4ed0-85d9-462f-b9cb+82a72f51c477@example.com',  # Subaddressing test
        ]
        self.existing_user = User.objects.create(
            recovery_email='e9fc8f36-8d9c-4e8c-9af2-2a7e2901b036@example.com',
            email='e9fc8f36-8d9c-4e8c-9af2-2a7e2901b036@example.org',
            username='e9fc8f36-8d9c-4e8c-9af2-2a7e2901b036@example.org',
        )
        for entry in self.wait_list:
            AllowListEntry.objects.create(email=entry)
        self.url = reverse('api_can_i_sign_up')

    def test_success(self):
        for email in self.wait_list:
            response = self.client.post(self.url, {'email': email})
            self.assertEqual(200, response.status_code)

            resp_data = response.json()
            self.assertEqual(
                CanISignUpResponses.SIGN_UP,
                resp_data.get('go_to'),
                f'{email} could not reach sign-up despite being on the wait list.',
            )

    def test_not_on_allowed_list(self):
        not_in_allowed_list = '45f46943-85ab-47fe-b5c0-56edd82e12fe@example.com'
        user_that_should_not_exist = User.objects.filter(recovery_email=not_in_allowed_list).first()
        self.assertIsNone(user_that_should_not_exist)

        response = self.client.post(self.url, {'email': not_in_allowed_list})

        self.assertEqual(200, response.status_code)

        resp_data = response.json()
        self.assertEqual(CanISignUpResponses.WAIT_LIST, resp_data.get('go_to'))

    def test_user_already_exists(self):
        self.assertIsNotNone(self.existing_user)

        response = self.client.post(self.url, {'email': self.existing_user.recovery_email})

        self.assertEqual(200, response.status_code)

        resp_data = response.json()
        self.assertEqual(CanISignUpResponses.LOGIN, resp_data.get('go_to'))


class CreateTestAllowListEntryTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api_create_test_allow_list_entry')
        self.user = User.objects.create(
            recovery_email=f'{uuid.uuid4()}@example.com', username=f'{uuid.uuid4()}@example.org'
        )
        self.permission_codename = 'create_test_entry_via_api'
        self.permission = Permission.objects.filter(codename=self.permission_codename).first()
        oidc_force_login(self.client, self.user)

    def _add_permission(self):
        # Required to access the route
        self.user.user_permissions.add(self.permission)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm(f'authentication.{self.permission_codename}'))

    def test_success(self):
        self._add_permission()

        email = f'test-{uuid.uuid4()}@example.com'

        response = self.client.post(self.url, {'email': email})
        self.assertEqual(200, response.status_code, response.content)

        resp_data = response.json()
        self.assertTrue(resp_data.get('success'))

        test_entry = AllowListEntry.objects.filter(email=email).first()
        self.assertIsNotNone(test_entry)
        self.assertTrue(test_entry.is_test_entry)  # ty:ignore[unresolved-attribute]

    def test_does_not_have_permission(self):
        self.assertFalse(self.user.has_perm(f'authentication.{self.permission_codename}'))

        email = f'test-{uuid.uuid4()}@example.com'

        response = self.client.post(self.url, {'email': email})
        self.assertEqual(403, response.status_code)

        test_entry = AllowListEntry.objects.filter(email=email).first()
        self.assertIsNone(test_entry)

    def test_invalid_emails_dont_get_added(self):
        self._add_permission()

        bad_emails = [
            f'@-{uuid.uuid4()}@example.com',  # An @ symbol isn't allowed in the local part
            {uuid.uuid4()},  # Needs to be a full email
            'a@example.com',  # Needs to be at least 3 characters
            'admin@example.org',  # Reserved name
            self.user.username,  # Already in use
        ]

        for email in bad_emails:
            response = self.client.post(self.url, {'email': email})
            self.assertEqual(400, response.status_code, f'Invalid email {email} returned {response.content}')

            resp_data = response.json()

            # Ensure we got the bad-email error and that our allow list entry was not created
            self.assertEqual('bad-email', resp_data.get('type'))
            test_entry = AllowListEntry.objects.filter(email=email).first()
            self.assertIsNone(test_entry)

    def test_missing_emails_just_error_out(self):
        self._add_permission()

        email = ''

        response = self.client.post(self.url, {'email': email})
        self.assertEqual(400, response.status_code, response.content)

        resp_data = response.json()

        # Ensure we got the bad-email error and that our allow list entry was not created
        self.assertEqual('no-email', resp_data.get('type'))
        test_entry = AllowListEntry.objects.filter(email=email).first()
        self.assertIsNone(test_entry)


class WaffleFlagsTestcase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api_waffle_flags')
        self.user = User.objects.create(
            oidc_id=str(uuid.uuid4()),
            recovery_email=f'{uuid.uuid4()}@example.com',
            username=f'{uuid.uuid4()}@example.org',
        )

        Flag.objects.create(name='flag-on-for-everyone', everyone=True)
        Flag.objects.create(name='flag-off-for-everyone', everyone=False)
        Flag.objects.create(name='flag-on-for-authenticated', authenticated=True)

        # Due to the endpoint being gated by OIDCAuthentication
        patcher = patch(
            'thunderbird_accounts.authentication.middleware.AccountsOIDCBackend.get_userinfo',
            side_effect=self._fake_userinfo,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _fake_userinfo(access_token, id_token, payload):
        # Mimic a real OIDC provider, which would reject unrecognized/invalid
        # access tokens rather than happily returning userinfo for anything.
        if not User.objects.filter(oidc_id=access_token).exists():
            raise SuspiciousOperation('invalid access token')

        return {
            'sub': access_token,
            'email': f'{access_token}@example.org',
            'email_verified': True,
            'preferred_username': f'{access_token}@example.org',
        }

    def test_returns_active_flags_for_authenticated_user(self):
        response = self.client.get(self.url, headers={'authorization': f'Bearer {self.user.oidc_id}'})
        self.assertEqual(200, response.status_code, response.content)

        flags = response.json().get('flags')
        self.assertEqual(
            {
                'flag-on-for-everyone',
                'flag-off-for-everyone',
                'flag-on-for-authenticated',
            },
            flags.keys(),
        )
        self.assertTrue(flags['flag-on-for-everyone']['is_active'])
        self.assertFalse(flags['flag-off-for-everyone']['is_active'])
        self.assertTrue(flags['flag-on-for-authenticated']['is_active'])

    def test_returns_active_flag_for_specific_user_only(self):
        other_user = User.objects.create(
            oidc_id=str(uuid.uuid4()),
            recovery_email=f'{uuid.uuid4()}@example.com',
            username=f'{uuid.uuid4()}@example.org',
        )

        flag = Flag.objects.create(name='flag-on-for-specific-user')
        flag.users.add(self.user)

        # Authenticate as the user created in the setup step and check that the flag is active
        response = self.client.get(self.url, headers={'authorization': f'Bearer {self.user.oidc_id}'})
        self.assertEqual(200, response.status_code, response.content)
        self.assertTrue(response.json()['flags']['flag-on-for-specific-user']['is_active'])

        # Authenticate as the other user and check that the flag is not active
        response = self.client.get(self.url, headers={'authorization': f'Bearer {other_user.oidc_id}'})
        self.assertEqual(200, response.status_code, response.content)
        self.assertFalse(response.json()['flags']['flag-on-for-specific-user']['is_active'])

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(401, response.status_code)

    def test_returns_401_for_invalid_token(self):
        response = self.client.get(self.url, headers={'authorization': 'Bearer invalid-token'})
        self.assertEqual(401, response.status_code)
