from json import JSONDecodeError
from unittest.mock import MagicMock, patch

from django.conf import settings
from urllib.parse import quote
from django.test import Client as RequestClient, override_settings
from rest_framework.test import APITestCase

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
            'timezone': 'UTC',
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
