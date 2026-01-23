from thunderbird_accounts.settings import USE_ALLOW_LIST
from unittest.mock import MagicMock, patch

import freezegun
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.forms import model_to_dict
from django.http import HttpRequest
from django.test import Client as RequestClient, override_settings
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from requests import Response

from thunderbird_accounts.authentication.admin import CustomUserAdmin
from thunderbird_accounts.authentication.clients import RequestMethods
from thunderbird_accounts.authentication.exceptions import ImportUserError
from thunderbird_accounts.authentication.middleware import AccountsOIDCBackend
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.reserved import is_reserved, servers, support
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.utils.tests.utils import build_keycloak_success_response
from thunderbird_accounts.authentication.models import AllowListEntry

FAKE_OIDC_UUID = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'


@patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
class AdminCreateUserTestCase(TestCase):
    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        self.default_form_data = dict({k.name: None for k in User()._meta.fields})

    def _build_form(self, form_data):
        user_admin = CustomUserAdmin(User, AdminSite())
        fake_request = HttpRequest()
        return user_admin.get_form(fake_request)(form_data)

    def _build_success_response(self):
        fake_uuid = FAKE_OIDC_UUID
        fake_url = 'http://example.org/admin/realms/tbpro'

        fake_response = Response()
        fake_response.status_code = 201
        fake_response.headers.update({'Location': f'{fake_url}/users/{fake_uuid}'})
        return fake_response

    def test_failed_username_validation(self, mock_requests: MagicMock):
        # Bad username
        form_data = {
            'username': 'frog',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

        mock_requests.assert_not_called()

    def test_failed_username_validation_reserved(self, mock_requests: MagicMock):
        # Bad username
        form_data = {
            'username': 'support@thundermail.com',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

        mock_requests.assert_not_called()

    def test_failed_email_validation(self, mock_requests: MagicMock):
        # Bad email domain
        form_data = {
            'username': 'frog@badexample.com',
            'email': 'frog@badexample.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        # ValueError: The User could not be created because the data didn't validate.
        with self.assertRaises(ValueError):
            form.save(True)

        # Check for invalid domain error
        self.assertTrue(len(form.errors) > 0)
        self.assertIn('Thundermail address must end with', str(form.errors))

        # No email
        form_data = {
            'username': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('email', form.errors)

        mock_requests.assert_not_called()

    def test_failed_timezone_validation(self, mock_requests: MagicMock):
        # Bad username
        form_data = {
            'username': 'frog',
            'email': 'frog@example.com',
            'timezone': 'America/Victoria',
        }

        form = self._build_form(form_data)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('timezone', form.errors)

        mock_requests.assert_not_called()

    def test_success(self, mock_requests: MagicMock):
        form_data = {
            'username': f'frog@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        mock_requests.return_value = build_keycloak_success_response(
            return_headers={'Location': f'http://keycloak:8999/admin/realms/tbpro/users/{FAKE_OIDC_UUID}'}
        )

        form = self._build_form(form_data)

        user = form.save(True)
        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Creating the user
        self.assertEqual(mock_requests.call_count, 1)

        # Ensure that our endpoint calls line up with our expectations above
        # ...yes it has that many tuples
        self.assertEqual(mock_requests.call_args_list[0][0][0], 'users')
        self.assertEqual(mock_requests.call_args_list[0][0][1], RequestMethods.POST)

    def test_success_with_reserved_username(self, mock_requests: MagicMock):
        form_data = {
            'username': f'admin@{self.subdomain}',
            'email': 'admin@example.com',
            'timezone': 'America/Toronto',
        }

        mock_requests.return_value = build_keycloak_success_response(
            return_headers={'Location': f'http://keycloak:8999/admin/realms/tbpro/users/{FAKE_OIDC_UUID}'}
        )

        form = self._build_form(form_data)

        user = form.save(True)
        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Creating the user
        self.assertEqual(mock_requests.call_count, 1)

        # Ensure that our endpoint calls line up with our expectations above
        # ...yes it has that many tuples
        self.assertEqual(mock_requests.call_args_list[0][0][0], 'users')


@patch('thunderbird_accounts.mail.clients.MailClient._update_principal')
@patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
class AdminUpdateUserTestcase(TestCase):
    """Tests the admin's user update form.
    We're mainly trying to make sure updates hit Keycloak as well."""

    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        # Create a test user so we can update it later
        self.user = User.objects.create(
            oidc_id=FAKE_OIDC_UUID, username=f'internaltest@{self.subdomain}', email='test@example.com'
        )
        self.user.save()
        self.user.refresh_from_db()

    def _build_form(self, form_data):
        user_admin = CustomUserAdmin(User, AdminSite())
        fake_request = HttpRequest()

        # Pass it an existing user and change=True for the update form
        # We also need ot pass it to the form as well (under instance)
        return user_admin.get_form(fake_request, self.user, change=True)(form_data, instance=self.user)

    def test_failed_invalid_timezone(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        form_data = {
            'username': f'frog@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Victoria',  # Bad timezone!
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = build_keycloak_success_response()
        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('timezone', form.errors)

        self.assertEqual(mock_update_principal.call_count, 0)

    def test_failed_empty_username(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        form_data = {
            'username': '',
            'email': self.user.email,
            'timezone': self.user.timezone,
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = build_keycloak_success_response()
        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('username', form.errors)

        self.assertEqual(mock_update_principal.call_count, 0)

    def test_failed_empty_email(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        form_data = {
            'username': self.user.username,
            'email': '',
            'timezone': self.user.timezone,
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = build_keycloak_success_response()
        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('email', form.errors)

        self.assertEqual(mock_update_principal.call_count, 0)

    def test_success(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        account = Account.objects.create(name='internaltest', user=self.user)
        Email.objects.create(
            address=self.user.username,
            type=Email.EmailType.PRIMARY,
            account=account,
        )

        old_username = self.user.username

        form_data = {
            'username': f'frog@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = build_keycloak_success_response()

        # Set the json output to an empty object
        mock_update_principal.return_value.json.return_value = {}

        form = self._build_form(form_data)
        user = form.save(True)

        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Retrieving existing user data
        # 2. Updating the user
        self.assertEqual(mock_requests.call_count, 2)

        # Ensure that our endpoint calls line up with our expectations above
        # ...yes it has that many tuples
        self.assertEqual(mock_requests.call_args[0][0], f'users/{self.user.oidc_id}')
        self.assertEqual(mock_requests.call_args[0][1], RequestMethods.PUT)

        # 2. Updating stalwart
        self.assertEqual(mock_update_principal.call_count, 1)
        self.assertEqual(mock_update_principal.call_args[0][0], old_username)
        self.assertEqual(mock_update_principal.call_args[0][1][0].get('value'), form_data.get('username'))

    def test_success_without_stalwart_account(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        form_data = {
            'username': f'frog@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = build_keycloak_success_response()

        # Set the json output to an empty object
        mock_update_principal.return_value.json.return_value = {}

        form = self._build_form(form_data)

        user = form.save(True)

        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Retrieving existing user data
        # 2. Updating the user
        self.assertEqual(mock_requests.call_count, 2)

        # Ensure that our endpoint calls line up with our expectations above
        # ...yes it has that many tuples
        self.assertEqual(mock_requests.call_args[0][0], f'users/{self.user.oidc_id}')
        self.assertEqual(mock_requests.call_args[0][1], RequestMethods.PUT)

        # 2. No update to stalwart
        self.assertEqual(mock_update_principal.call_count, 0)

    def test_success_without_username_update(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        account = Account.objects.create(name='internaltest', user=self.user)
        Email.objects.create(
            address=self.user.username,
            type=Email.EmailType.PRIMARY,
            account=account,
        )

        form_data = {
            'username': f'internaltest@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = build_keycloak_success_response()

        # Set the json output to an empty object
        mock_update_principal.return_value.json.return_value = {}

        form = self._build_form(form_data)

        user = form.save(True)

        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Retrieving existing user data
        # 2. Updating the user
        self.assertEqual(mock_requests.call_count, 2)

        # Ensure that our endpoint calls line up with our expectations above
        # ...yes it has that many tuples
        self.assertEqual(mock_requests.call_args[0][0], f'users/{self.user.oidc_id}')
        self.assertEqual(mock_requests.call_args[0][1], RequestMethods.PUT)

        # 2. No update to stalwart
        self.assertEqual(mock_update_principal.call_count, 0)


@patch('thunderbird_accounts.mail.clients.MailClient._delete_principal')
@patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
class AdminDeleteUserTestCase(TestCase):
    """Tests the admin user delete action.
    This is just a function/unit test as there's no form involved here."""

    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN

        self.user = User.objects.create(
            oidc_id=FAKE_OIDC_UUID, username=f'test@{self.subdomain}', email='test@example.com'
        )
        self.user.save()
        self.user.refresh_from_db()

    def _build_admin_model(self):
        return CustomUserAdmin(User, AdminSite())

    def _build_fake_request(self):
        return HttpRequest()

    def _main_test(self):
        self.assertIsNotNone(self.user)

        user_admin = self._build_admin_model()
        user_admin.delete_model(self._build_fake_request(), self.user)

        with self.assertRaises(User.DoesNotExist):
            self.user.refresh_from_db()

    def test_success(self, mock_requests: MagicMock, mock_delete_principal: MagicMock):
        """Tests the full deletion flow:
        1. Delete the User model.
        2. Send a delete request to Keycloak to remove their login.
        3. Send a delete request to Stalwart to remove their email/inbox."""
        account = Account.objects.create(name='test', user=self.user)
        email = Email.objects.create(
            address=self.user.username,
            type=Email.EmailType.PRIMARY,
            account=account,
        )

        self._main_test()

        mock_requests.assert_called_once()

        endpoint, method = mock_requests.call_args[0]
        self.assertEqual(endpoint, f'users/{FAKE_OIDC_UUID}')
        self.assertEqual(method, RequestMethods.DELETE)

        mock_delete_principal.assert_called_once()

        with self.assertRaises(Account.DoesNotExist):
            account.refresh_from_db()
        with self.assertRaises(Email.DoesNotExist):
            email.refresh_from_db()

    def test_success_without_stalwart_account(self, mock_requests: MagicMock, mock_delete_principal: MagicMock):
        """Tests a partial deletion flow since the user does not have a Stalwart email/inbox setup.
        1. Delete the User model.
        2. Send a delete request to Keycloak to remove their login.
        3. Make sure we didn't send anything to Stalwart
        """
        self._main_test()

        mock_requests.assert_called_once()

        endpoint, method = mock_requests.call_args[0]
        self.assertEqual(endpoint, f'users/{FAKE_OIDC_UUID}')
        self.assertEqual(method, RequestMethods.DELETE)

        mock_delete_principal.assert_not_called()


@override_settings(USE_ALLOW_LIST=True)
class AccountsOIDCBackendTestCase(TestCase):
    def setUp(self):
        self.claim_oidc_id = 'abc123'
        self.claim_email = 'user@example.org'
        with freezegun.freeze_time('Apr 4th, 2000'):
            self.user = User.objects.create(
                oidc_id=self.claim_oidc_id, username='test@example.org', email=self.claim_email
            )
            self.user.save()
            self.user.refresh_from_db()
        self.backend = AccountsOIDCBackend()
        self.backend.request = HttpRequest()
        self.backend.request._messages = MagicMock()

        # Remove any allow list entries
        AllowListEntry.objects.all().delete()


    def test_create_user_success(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'zoneinfo': 'America/Vancouver',
            'email_verified': True,
            'name': 'Admin Example',
            'preferred_username': 'admin@example.org',
            'session_state': '196cb668-5492-4fd1-811b-72fdae44fd39',
            'given_name': 'Admin',
            'locale': 'en',
            'family_name': 'Example',
            'email': 'admin@example.com',
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = self.backend.create_user(claims)
        self.assertIsNotNone(user)

        self.assertEqual(user.email, claims.get('email'))
        self.assertEqual(user.username, claims.get('preferred_username'))
        self.assertEqual(user.display_name, claims.get('preferred_username'))
        self.assertEqual(user.get_full_name(), claims.get('name'))
        self.assertEqual(user.oidc_id, claims.get('sub'))
        self.assertEqual(user.language, claims.get('locale'))
        self.assertEqual(user.timezone, claims.get('zoneinfo'))

        # is_services_admin wasn't included in the claim, and the default create_user value is False
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_success_bare_minimum(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = self.backend.create_user(claims)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, claims.get('email'))
        self.assertEqual(user.username, claims.get('preferred_username'))
        self.assertEqual(user.display_name, claims.get('preferred_username'))
        self.assertEqual(user.oidc_id, claims.get('sub'))

    def test_create_user_fail_on_no_verified_email(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': False,
        }

        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)

    def test_create_user_fail_on_not_on_allow_list(self):
        # Just here to demonstrate that this user isn't on the allow list
        AllowListEntry.objects.create(email='admin@example.ca')
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': False,
        }

        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)

    def test_create_user_superuser_access(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
            'is_services_admin': 'yes',
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = self.backend.create_user(claims)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_update_user_success(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
            # New data!
            'given_name': 'Example Admin',
            'is_services_admin': 'yes',
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_staff=False,
            is_superuser=False,
        )
        # Retrieve a copy of the fields as update_user will update this instance.
        user_data = model_to_dict(user)

        user_updated = self.backend.update_user(user, claims)

        self.assertIsNotNone(user_updated)

        # Make sure these values are fixed
        self.assertFalse(user_data.get('is_staff'))
        self.assertFalse(user_data.get('is_superuser'))

        # Make sure nothing else has changed
        self.assertEqual(user_updated.email, user_data.get('email'))
        self.assertEqual(user_updated.username, user_data.get('username'))
        self.assertEqual(user_updated.display_name, user_data.get('display_name'))
        self.assertEqual(user_updated.oidc_id, user_data.get('oidc_id'))

        # Make sure these fields have changed
        self.assertNotEqual(user_updated.first_name, user_data.get('first_name'))
        self.assertNotEqual(user_updated.is_staff, user_data.get('is_staff'))
        self.assertNotEqual(user_updated.is_superuser, user_data.get('is_superuser'))

    def test_update_user_dont_reset_services_admin_permissions(self):
        """Testing update_user to make sure not including is_services_admin in claim will leave is_staff,
        and is_superuser fields alone."""
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
        }

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_staff=True,
            is_superuser=True,
        )
        # Retrieve a copy of the fields as update_user will update this instance.
        user_data = model_to_dict(user)

        user_updated = self.backend.update_user(user, claims)

        self.assertIsNotNone(user_updated)

        # Make sure these values are fixed
        self.assertTrue(user_data.get('is_staff'))
        self.assertTrue(user_data.get('is_superuser'))

        # Make sure these fields have not changed
        self.assertTrue(user_updated.is_staff)
        self.assertTrue(user_updated.is_superuser)

    def test_update_active_user_doesnt_check_allowlist(self):
        """Testing update_user to make sure not including is_services_admin in claim will leave is_staff,
        and is_superuser fields alone."""
        settings.AUTH_ALLOW_LIST = 'example.org'
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@not_in_allow_list_example.com',
            'email_verified': True,
        }

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_active=True,
        )

        user_updated = self.backend.update_user(user, claims)
        self.assertIsNotNone(user_updated)
        settings.AUTH_ALLOW_LIST = ''

    def test_update_inactive_user_does_check_allowlist(self):
        """Testing update_user to make sure not including is_services_admin in claim will leave is_staff,
        and is_superuser fields alone."""
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@not_in_allow_list_example.com',
            'email_verified': True,
        }

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_active=False,
        )

        with self.assertRaises(PermissionDenied):
            self.backend.update_user(user, claims)

    def test_filter_users_by_claims_no_fallback(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = False

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})
        assert len(query) == 1

        query = self.backend.filter_users_by_claims(
            {'sub': f'{self.claim_oidc_id}_not_the_actual_id_anymore', 'email': self.claim_email}
        )
        assert len(query) == 0

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting

    def test_filter_users_by_claims_with_fallback(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = True

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})
        assert len(query) == 1

        query = self.backend.filter_users_by_claims(
            {'sub': f'{self.claim_oidc_id}_not_the_actual_id_anymore', 'email': self.claim_email}
        )
        assert len(query) == 1

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting

    def test_filter_users_by_claims_with_fallback_with_duplicates(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = True

        # Ensure the user doesn't have an oidc id
        self.user.oidc_id = None
        self.user.save()

        user_duplicates = [
            User.objects.create(oidc_id=None, email=self.claim_email, username='test'),
            User.objects.create(oidc_id=None, email=self.claim_email, username='test2'),
            User.objects.create(oidc_id=None, email=self.claim_email, username='test3'),
        ]

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})

        assert len(query) == 1
        self.assertEqual(self.user.pk, query[0].pk)
        self.assertEqual(self.claim_email, query[0].email)

        # Ensure the older models were deleted
        for user in user_duplicates:
            with self.assertRaises(User.DoesNotExist):
                user.refresh_from_db()

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting


class IsReservedUnitTests(TestCase):
    def test_brand_names(self):
        for brand in ['thunderbird', 'mozilla', 'firefox', 'help', 'support', 'mzla']:
            self.assertTrue(is_reserved(brand))

    def test_brand_plus_variants(self):
        # (brands)? allows more than one match
        for name in ['thunderbirdthunderbird', 'supportsupport']:
            self.assertFalse(is_reserved(name))

    def test_brand_support_help_suffix_patterns(self):
        # ^(brand).*support?$ and customer_support and help
        for name in [
            'thunderbirdpro_customer_support',
            'thunderbirdpro_support',
            'thunderbird_customer_support',
            'thunderbird_support',
            'thunderbird-support',
            'mzla_support',
            'mzla_help',
            'mozilla_support',
            'firefox_help',
        ]:
            self.assertTrue(is_reserved(name))

        # ^(brand).*email?$ and ^(brand).*org?$
        for name in ['thunderbird_email', 'firefox_org']:
            self.assertTrue(is_reserved(name), name)

    def test_official_and_real_variants(self):
        for name in [
            'official_thunderbird',
            'officialsupport',
            'realmozilla',
            'firefox_real',
            'support_official',
            'mozilla_real',
        ]:
            self.assertTrue(is_reserved(name))

    def test_mzla_test_variants(self):
        for name in ['mzla-test', 'mzla-test.123', 'mzla-test.alpha.beta']:
            self.assertTrue(is_reserved(name))

    def test_common_example_usernames(self):
        for name in ['username', 'user_name', 'user', 'exampleuser', 'example_name', 'example-user', 'test']:
            self.assertTrue(is_reserved(name))

    def test_servers(self):
        for name in ['admin', 'root', 'webmaster', 'postmaster', 'superuser', 'administrator']:
            self.assertTrue(is_reserved(name))

    def test_team_and_contact(self):
        for name in [
            'team',
            'hr',
            'accounts_team',
            'engineering',
            'engineering_team',
            'marketing_team',
            'design',
            'design_team',
            'contactus',
            'contact_us',
        ]:
            self.assertTrue(is_reserved(name))

    def test_internal_names(self):
        # select a few to hardcode test
        for name in ['root', 'postmaster', 'support', 'marketing']:
            self.assertTrue(is_reserved(name), name)

        for name in servers + support:
            self.assertTrue(is_reserved(name), name)

    def test_birbs(self):
        for name in ['roc', 'ezio', 'mithu', 'ava', 'callum', 'sora', 'robin', 'nemo']:
            self.assertTrue(is_reserved(name))

    def test_non_reserved(self):
        reserved_names_related = ['mozillafan', 'supporter', 'helper', 'hostmastery', 'contacts']
        unrelated = ['randomuser', 'this_should_not_be_a_problem', '123_asdf', 'asdf_123', '123asdf', 'asdf123']
        for name in reserved_names_related + unrelated:
            self.assertFalse(is_reserved(name))

    def test_partial_matches_should_pass(self):
        # Anchors ^...$ mean full-string match only
        for name in ['user123', 'myusernamex', 'rooted', 'teamwork', 'contacting']:
            self.assertFalse(is_reserved(name))


@override_settings(USE_ALLOW_LIST=True)
@patch('thunderbird_accounts.authentication.clients.KeycloakClient.import_user')
class SignUpViewTestcase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.wait_list = ['hello@example.com', 'hello2@example.com']
        for entry in self.wait_list:
            AllowListEntry.objects.create(email=entry)

    def get_messages(self, response):
        """Little helper message to retrieve flash messages"""
        return list(messages.get_messages(response.wsgi_request))

    def test_success(self, mock_import_user: MagicMock):
        """Test that an unauthenticated user can sign-up if they're in the allow list."""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        response = self.client.post(
            '/users/sign-up/',
            {
                'email': self.wait_list[0],
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': 'hello',
                'password': '123',
                'password-confirm': '123',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get('Location'), '/sign-up/complete', msg=self.get_messages(response))

    def test_not_on_allowed_list(self, mock_import_user: MagicMock):
        """Test that a recovery email not on the allow list will ship them to the wait list"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        response = self.client.post(
            '/users/sign-up/',
            {
                'email': 'hello3@example.com',
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': 'hello',
                'password': '123',
                'password-confirm': '123',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers.get('Location'), settings.TB_PRO_WAIT_LIST_URL, msg=self.get_messages(response)
        )

    def test_user_already_exists(self, mock_import_user: MagicMock):
        """Test that we check if a user exists before creating a user"""

        User(email=self.wait_list[0], username='hello@example.org').save()

        response = self.client.post(
            '/users/sign-up/',
            {
                'email': self.wait_list[0],
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': 'hello',
                'password': '123',
                'password-confirm': '123',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get('Location'), '/sign-up', msg=self.get_messages(response))
        self.assertEqual(str(_('You cannot sign-up with that email address.')), self.get_messages(response)[0].message)

    def test_passwords_are_empty(self, mock_import_user: MagicMock):
        """Test that we check if passwords exist"""

        response = self.client.post(
            '/users/sign-up/',
            {'email': self.wait_list[0], 'timezone': 'UTC', 'locale': 'en', 'partialUsername': 'hello'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get('Location'), '/sign-up', msg=self.get_messages(response))
        self.assertEqual(
            str(_("Your password doesn't match the confirm password field.")), self.get_messages(response)[0].message
        )

    def test_passwords_dont_match(self, mock_import_user: MagicMock):
        """Test that we check if passwords actually match"""

        response = self.client.post(
            '/users/sign-up/',
            {
                'email': self.wait_list[0],
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': 'hello',
                'password': '1',
                'password-confirm': '2',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get('Location'), '/sign-up', msg=self.get_messages(response))
        self.assertEqual(
            str(_("Your password doesn't match the confirm password field.")), self.get_messages(response)[0].message
        )

    def test_import_errors_propagate(self, mock_import_user: MagicMock):
        """Test to make sure keycloak import user errors propagate to the frontend via messages"""
        mock_test_error = 'This is a test error.'
        mock_import_user.side_effect = ImportUserError(
            'Test Error', username='hello', error_code='TEST', error_desc=mock_test_error
        )
        response = self.client.post(
            '/users/sign-up/',
            {
                'email': self.wait_list[0],
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': 'hello',
                'password': '123',
                'password-confirm': '123',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get('Location'), '/sign-up', msg=self.get_messages(response))
        self.assertEqual(mock_test_error, self.get_messages(response)[0].message)
