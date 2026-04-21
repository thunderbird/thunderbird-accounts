from unittest.mock import MagicMock, patch

import freezegun
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.forms import model_to_dict
from django.http import HttpRequest
from urllib.parse import quote
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
from thunderbird_accounts.core.tests.utils import build_keycloak_success_response
from thunderbird_accounts.authentication.models import AllowListEntry

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

        mock_user_email = 'hello3@example.com'

        # Redirect should include mock user's email in querystring
        waitlist_url = f'{settings.TB_PRO_WAIT_LIST_URL}?email={quote(mock_user_email)}'

        response = self.client.post(
            '/users/sign-up/',
            {
                'email': mock_user_email,
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': 'hello',
                'password': '123',
                'password-confirm': '123',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get('Location'), waitlist_url, msg=self.get_messages(response))

    def test_user_already_exists(self, mock_import_user: MagicMock):
        """Test that we check if a user exists before creating a user"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

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

    def test_alias_already_exists(self, mock_import_user: MagicMock):
        """Test that we check if a alias exists before creating a user"""

        # Set a return value for oidc_id
        mock_import_user.return_value = 1

        alias = 'not_in_examples'

        user = User(email='not_in_examples@example.org', username=f'{alias}@example.org').save()
        account = Account(name='{alias}@example.org', user=user).save()
        Email(address=self.wait_list[0], type=Email.EmailType.ALIAS, account=account).save()

        response = self.client.post(
            '/users/sign-up/',
            {
                'email': self.wait_list[0],
                'timezone': 'UTC',
                'locale': 'en',
                'partialUsername': alias,
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
