import json
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.http import JsonResponse
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.utils.tests.utils import oidc_force_login


class PaddleCheckoutCompleteTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        oidc_force_login(self.client, self.user)
        self.url = reverse('paddle_complete')

    @override_settings(IS_DEV=False)
    def test_success_not_dev(self):
        with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
            instance = paddle_client_mock()

            response = self.client.get(
                self.url,
                follow=False,
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/dashboard')
            instance.notifications.list.assert_not_called()

    @patch('time.sleep', MagicMock())
    @patch('thunderbird_accounts.subscription.tasks.paddle_subscription_event', MagicMock())
    @override_settings(IS_DEV=True)
    def test_success_dev(self):
        """Simple test, this doesn't actually test if we've got the correct data, it just makes sure we don't crash"""
        txid = 'abc123'
        txid_response: JsonResponse = self.client.put(reverse('paddle_txid'), data=json.dumps({'txid': txid}))
        self.assertEqual(txid_response.status_code, 200)
        self.assertEqual(json.loads(txid_response.content), {'success': True})

        # Don't actually send anything to Paddle!
        with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
            instance = paddle_client_mock()

            response = self.client.get(
                self.url,
                follow=False,
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/dashboard')
            instance.notifications.list.assert_called()

    @patch('time.sleep', MagicMock())
    @patch('thunderbird_accounts.subscription.tasks.paddle_subscription_event', MagicMock())
    @override_settings(IS_DEV=True)
    def test_fail_without_txid_dev(self):
        """We don't have a transaction id in the session, so we are sent back to /subscribe

        We can't handle these requests because we need the transaction id to fill in paddle subscription data"""
        response = self.client.get(
            self.url,
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/subscribe')
