from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.authentication.models import User
from django.urls import reverse
from unittest.mock import patch

from django.test import override_settings, Client as RequestClient
from rest_framework.test import APITestCase


@override_settings(CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=True)
class CheckEmailIsOnAllowListApiTestCase(APITestCase):
    def setUp(self):
        self.client = RequestClient()
        self.url = '/api/v1/contact/check-email-is-on-allow-list/'

    def test_missing_email_returns_validation_error(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 400)
        self.assertIn('You need to enter an email address.', str(response.json()))

    @patch('thunderbird_accounts.mail.api.is_email_in_allow_list')
    def test_returns_true_when_email_is_on_allow_list(self, mock_is_email_in_allow_list):
        mock_is_email_in_allow_list.return_value = True
        email = 'allowed@example.com'

        response = self.client.post(self.url, {'email': email})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'is_on_allow_list': True})
        mock_is_email_in_allow_list.assert_called_once_with(email)

    @patch('thunderbird_accounts.mail.api.is_email_in_allow_list')
    def test_returns_false_when_email_is_not_on_allow_list(self, mock_is_email_in_allow_list):
        mock_is_email_in_allow_list.return_value = False
        email = 'not-allowed@example.com'

        response = self.client.post(self.url, {'email': email})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'is_on_allow_list': False})
        mock_is_email_in_allow_list.assert_called_once_with(email)

    @override_settings(CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=False)
    @patch('thunderbird_accounts.mail.api.is_email_in_allow_list')
    def test_returns_true_without_checking_allow_list_when_restriction_is_disabled(
        self,
        mock_is_email_in_allow_list,
    ):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'is_on_allow_list': True})
        mock_is_email_in_allow_list.assert_not_called()


class IsUsernameAvailableTestCase(APITestCase):
    def setUp(self):
        self.client = RequestClient()
        self.url = reverse('api_is_username_available')

    def test_success(self):
        """Use a username that no one else has"""
        response = self.client.post(self.url, {'username': 'hello'})
        self.assertEqual(response.status_code, 200)

    def test_reserved_word(self):
        """Fail on a reserved word like admin or thunderbird"""
        response = self.client.post(self.url, {'username': 'thunderbird'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()[0], 'This username is not valid. Try another one.')

    def test_in_use_username(self):
        """Fail on an in-use username"""
        # Create a user with an in-use username
        user = User.objects.create(username='fred@example.org')

        response = self.client.post(self.url, {'username': user.username.split('@')[0]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()[0], 'This username is already taken. Try another one.')

    def test_in_use_alias(self):
        """Fail on an alias that is already in-use"""
        # Create a user with an in-use username
        user = User.objects.create(username='fred@example.org')
        account = Account.objects.create(name=user.username, user=user)
        email = Email.objects.create(address='fred-is-cool@example.org', type=Email.EmailType.ALIAS, account=account)

        response = self.client.post(self.url, {'username': email.address.split('@')[0]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()[0], 'This username is already taken. Try another one.')
