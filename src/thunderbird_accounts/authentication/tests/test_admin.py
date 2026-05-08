from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.admin import AdminSite
from django.http import HttpRequest
from django.test import TestCase

from requests import Response

from thunderbird_accounts.authentication.admin import CustomUserAdmin
from thunderbird_accounts.authentication.clients import RequestMethods
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.core.tests.utils import build_keycloak_success_response

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
            'recovery_email': 'frog@example.com',
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
            'recovery_email': 'frog@example.com',
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
            'recovery_email': 'frog@badexample.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        # ValueError: The User could not be created because the data didn't validate.
        with self.assertRaises(ValueError):
            form.save(True)

        # Check for invalid domain error
        self.assertTrue(len(form.errors) > 0)
        self.assertIn('Thundermail address must end with', str(form.errors))

        # No recovery email
        form_data = {
            'username': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('recovery_email', form.errors)

        mock_requests.assert_not_called()

    def test_failed_timezone_validation(self, mock_requests: MagicMock):
        # Bad username
        form_data = {
            'username': 'frog',
            'recovery_email': 'frog@example.com',
            'timezone': 'America/Victoria',
        }

        form = self._build_form(form_data)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('timezone', form.errors)

        mock_requests.assert_not_called()

    def test_success(self, mock_requests: MagicMock):
        form_data = {
            'username': f'frog@{self.subdomain}',
            'recovery_email': 'frog@example.com',
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
            'recovery_email': 'admin@example.com',
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
            'recovery_email': 'frog@example.com',
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
            'recovery_email': self.user.email,
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
            'recovery_email': '',
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
        self.assertIn('recovery_email', form.errors)

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
            'recovery_email': 'frog@example.com',
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
            'recovery_email': 'frog@example.com',
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
            'recovery_email': 'frog@example.com',
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

