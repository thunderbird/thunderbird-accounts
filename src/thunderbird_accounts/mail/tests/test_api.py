from unittest.mock import patch

from django.test import Client as RequestClient
from rest_framework.test import APITestCase


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
