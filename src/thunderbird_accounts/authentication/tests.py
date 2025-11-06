from unittest.mock import patch, MagicMock

import freezegun
from django.conf import settings
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.forms import model_to_dict
from django.http import HttpRequest
from django.test import TestCase, Client as RequestClient
from django.urls import reverse
from requests import Response

from thunderbird_accounts.authentication.admin import CustomUserAdmin
from thunderbird_accounts.authentication.clients import RequestMethods
from thunderbird_accounts.authentication.middleware import AccountsOIDCBackend
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Email

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

        mock_requests.return_value = self._build_success_response()

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


@patch('thunderbird_accounts.mail.clients.MailClient._update_principal')
@patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
class AdminUpdateUserTestcase(TestCase):
    """Tests the admin's user update form.
    We're mainly trying to make sure updates hit Keycloak as well."""

    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        # Create a test user so we can update it later
        self.user = User.objects.create(
            oidc_id=FAKE_OIDC_UUID, username=f'test@{self.subdomain}', email='test@example.com'
        )
        self.user.save()
        self.user.refresh_from_db()

    def _build_success_response(self):
        fake_response = Response()
        fake_response.status_code = 200
        return fake_response

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

        mock_requests.return_value = self._build_success_response()
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

        mock_requests.return_value = self._build_success_response()
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

        mock_requests.return_value = self._build_success_response()
        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('email', form.errors)

        self.assertEqual(mock_update_principal.call_count, 0)

    def test_success(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        account = Account.objects.create(name='test', user=self.user)
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

        mock_requests.return_value = self._build_success_response()

        # Set the json output to an empty object
        mock_update_principal.return_value.json.return_value = {}

        form = self._build_form(form_data)

        user = form.save(True)

        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Updating the user
        self.assertEqual(mock_requests.call_count, 1)

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

        mock_requests.return_value = self._build_success_response()

        # Set the json output to an empty object
        mock_update_principal.return_value.json.return_value = {}

        form = self._build_form(form_data)

        user = form.save(True)

        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Updating the user
        self.assertEqual(mock_requests.call_count, 1)

        # Ensure that our endpoint calls line up with our expectations above
        # ...yes it has that many tuples
        self.assertEqual(mock_requests.call_args[0][0], f'users/{self.user.oidc_id}')
        self.assertEqual(mock_requests.call_args[0][1], RequestMethods.PUT)

        # 2. No update to stalwart
        self.assertEqual(mock_update_principal.call_count, 0)

    def test_success_without_username_update(self, mock_requests: MagicMock, mock_update_principal: MagicMock):
        account = Account.objects.create(name='test', user=self.user)
        Email.objects.create(
            address=self.user.username,
            type=Email.EmailType.PRIMARY,
            account=account,
        )

        form_data = {
            'username': f'test@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
            'oidc_id': self.user.oidc_id,
            # This is dumb, the fields are split into 2 and are populated via existing data
            # But we need to provide it as form data otherwise it'll error out.
            'date_joined_0': self.user.date_joined.date(),
            'date_joined_1': self.user.date_joined.time(),
        }

        mock_requests.return_value = self._build_success_response()

        # Set the json output to an empty object
        mock_update_principal.return_value.json.return_value = {}

        form = self._build_form(form_data)

        user = form.save(True)

        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)

        # 1. Updating the user
        self.assertEqual(mock_requests.call_count, 1)

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

    def test_create_user_fail_on_not_in_allow_list(self):
        settings.AUTH_ALLOW_LIST = 'not_example.org'
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
        }

        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)

    def test_create_user_fail_on_not_on_allow_list(self):
        _original_settings = settings.ALLOWED_EMAIL_DOMAINS
        settings.ALLOWED_EMAIL_DOMAINS = ['example.ca']
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': False,
        }

        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)

        settings.ALLOWED_EMAIL_DOMAINS = _original_settings

    def test_create_user_superuser_access(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
            'is_services_admin': 'yes',
        }

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

    def test_update_inactive_user_does_check_allowlist(self):
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


class LoginRequiredTestCase(TestCase):
    # (URL reverse key, expected response status code),
    login_required_keys = [
        ('self_serve_home', 302),  # This one is a redirect
        ('self_serve_account_info', 302),
        ('self_serve_app_password', 302),
        ('self_serve_connection_info', 302),
        ('self_serve_subscription', 302),
        ('self_serve_subscription_success', 302),
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
