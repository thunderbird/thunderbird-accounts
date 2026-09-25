from thunderbird_accounts.subscription.models import Plan, Subscription, Transaction
import json
import requests
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.models import AllowListEntry
from thunderbird_accounts.core.tests.utils import oidc_force_login


class PaddleCheckoutIsDoneTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        oidc_force_login(self.client, self.user)
        self.url = reverse('paddle_is_done')
        self.txid = 'abc123'

    def set_paddle_transaction_id(self):
        """This actually tests set_paddle_transaction_id too!"""
        txid_response = self.client.put(reverse('paddle_txid'), data=json.dumps({'txid': self.txid}))
        self.assertEqual(txid_response.status_code, 200)
        data = txid_response.json()
        self.assertTrue(data.get('success'))

    def test_set_paddle_transaction_id_rejects_invalid_json(self):
        response = self.client.put(
            reverse('paddle_txid'),
            data='invalid json',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'success': False, 'error': 'Invalid request data'})

    def test_set_paddle_transaction_id_rejects_invalid_utf8(self):
        response = self.client.put(
            reverse('paddle_txid'),
            data=b'\x80',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'success': False, 'error': 'Invalid request data'})

    @override_settings(IS_DEV=False)
    def test_no_tx_id_in_session(self):
        """This route requires a transaction id in their session. So if they don't have a transaction id,
        we'll respond accordingly."""
        with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
            instance = paddle_client_mock()

            response = self.client.post(
                self.url,
                follow=False,
            )
            self.assertTrue(response)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data)
            self.assertEqual(data.get('status'), 'no-id?')

            instance.notifications.list.assert_not_called()

    @override_settings(IS_DEV=False)
    def test_no_tx_in_db(self):
        """This route should still return correctly (as draft) if there's no transaction in our db.
        We should also ensure IS_DEV=False does not call Paddle."""

        # Make sure we have a txid in session
        self.set_paddle_transaction_id()

        with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
            instance = paddle_client_mock()

            response = self.client.post(
                self.url,
                follow=False,
            )
            self.assertTrue(response)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data)
            self.assertEqual(data.get('status'), Transaction.StatusValues.DRAFT.value)

            instance.notifications.list.assert_not_called()

    @override_settings(IS_DEV=False)
    def test_user_payment_already_being_verified(self):
        """This route shouldn't run and instead return PAID if we're awaiting the Paddle webhook.
        Additionally we don't set a transaction id here because we explicitly
        remove it when we set the awaiting payment verification flag."""

        self.user.is_awaiting_payment_verification = True
        self.user.save()

        with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
            instance = paddle_client_mock()

            response = self.client.post(
                self.url,
                follow=False,
            )
            self.assertTrue(response)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data)
            self.assertEqual(data.get('status'), Transaction.StatusValues.PAID.value)

            instance.notifications.list.assert_not_called()

    @override_settings(IS_DEV=False)
    def test_transaction_found_but_not_doneish(self):
        """We found the transaction but it's not done enough for us to consider it done.
        We should also ensure IS_DEV=False does not call Paddle."""

        # Make sure we have a txid in session
        self.set_paddle_transaction_id()

        transaction = Transaction.objects.create(paddle_id=self.txid, status=Transaction.StatusValues.READY.value)
        self.assertIsNotNone(transaction)

        with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
            instance = paddle_client_mock()

            response = self.client.post(
                self.url,
                follow=False,
            )
            self.assertTrue(response)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data)
            self.assertEqual(data.get('status'), Transaction.StatusValues.READY.value)

            instance.notifications.list.assert_not_called()


class PaddleInformationTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(
            username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}',
            recovery_email='recovery@example.com',
            oidc_id='1234',
        )
        oidc_force_login(self.client, self.user)
        self.url = reverse('paddle_info')

    def test_includes_discount_id_from_allow_list_entry(self):
        AllowListEntry.objects.create(email='recovery@example.com', user=self.user, discount_id='dsc_123')

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('discount_id'), 'dsc_123')

    def test_includes_null_discount_id_when_not_set(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json().get('discount_id'))


class PaddleTransactionCompleteCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(
            username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234', is_awaiting_payment_verification=False
        )
        oidc_force_login(self.client, self.user)
        self.url = reverse('paddle_completed')
        self.txid = 'abc123'

    def set_paddle_transaction_session_data(self, payment_type):
        """This actually tests set_paddle_transaction_id too!"""
        txid_response = self.client.put(
            reverse('paddle_txid'), data=json.dumps({'txid': self.txid, 'payment_type': payment_type})
        )
        self.assertEqual(txid_response.status_code, 200)
        data = txid_response.json()
        self.assertTrue(data.get('success'))

    def _test_doneish_by_status(self, tx_status, is_popup_payment_provider=False):
        """Helper function so we can reduce some code without introducing artifacts between test runs."""
        # Make sure we have a txid and payment type in session
        payment_type = 'card' if not is_popup_payment_provider else 'paypal'
        ok_status_code = 200 if is_popup_payment_provider else 302
        ok_payment_verification = tx_status in [
            Transaction.StatusValues.PAID.value,
            Transaction.StatusValues.COMPLETED.value,
        ]

        self.set_paddle_transaction_session_data(payment_type)

        transaction = Transaction.objects.create(paddle_id=self.txid, status=tx_status.value)
        self.assertIsNotNone(transaction)

        with patch('thunderbird_accounts.subscription.tasks.dev_only_paddle_fake_webhook', MagicMock()) as task_mock:
            with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
                instance = paddle_client_mock()
                status_mock = MagicMock()

                status_mock.status = tx_status
                instance.transactions.get.return_value = status_mock

                self.assertFalse(self.user.is_awaiting_payment_verification)

                response = self.client.post(
                    self.url,
                    follow=False,
                )
                self.assertTrue(response)
                self.assertEqual(response.status_code, ok_status_code)

                self.user.refresh_from_db()
                self.assertEqual(self.user.is_awaiting_payment_verification, ok_payment_verification)

                instance.transactions.get.assert_called()
                instance.notifications.list.assert_not_called()
                task_mock.assert_not_called()

    @override_settings(IS_DEV=False)
    def test_transaction_found_and_is_not_doneish_by_being_ready(self):
        """We found the transaction but it's doneish (status=READY). This shouldn't do anything!

        We should also ensure IS_DEV=False does not call Paddle or the fake webhook task."""

        self._test_doneish_by_status(Transaction.StatusValues.READY)

    @override_settings(IS_DEV=False)
    def test_transaction_found_and_is_doneish_by_being_paid(self):
        """We found the transaction but it's doneish (status=PAID). This should trigger payment verification
        and remove txid from session.

        We should also ensure IS_DEV=False does not call Paddle or the fake webhook task."""

        self._test_doneish_by_status(Transaction.StatusValues.PAID)

    @override_settings(IS_DEV=False)
    def test_transaction_found_and_is_doneish_by_being_completed(self):
        """We found the transaction but it's doneish (status=COMPLETED). This should trigger payment verification
        and remove txid from session.

        We should also ensure IS_DEV=False does not call Paddle or the fake webhook task."""

        self._test_doneish_by_status(Transaction.StatusValues.COMPLETED)

    @override_settings(IS_DEV=False)
    def test_transaction_found_and_is_doneish_by_being_paid_popup_popup_edition(self):
        """We found the transaction but it's doneish (status=PAID). This should trigger payment verification
        and remove txid from session.

        We should also ensure IS_DEV=False does not call Paddle or the fake webhook task."""

        self._test_doneish_by_status(Transaction.StatusValues.PAID, True)

    @override_settings(IS_DEV=False)
    def test_transaction_found_and_is_doneish_by_being_completed_popup_edition(self):
        """We found the transaction but it's doneish (status=COMPLETED). This should trigger payment verification
        and remove txid from session.

        We should also ensure IS_DEV=False does not call Paddle or the fake webhook task."""

        self._test_doneish_by_status(Transaction.StatusValues.COMPLETED, True)


class ActiveSubscriptionRequiredViewTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        oidc_force_login(self.client, self.user)

    def test_paddle_portal_link_requires_active_subscription(self):
        response = self.client.post(reverse('paddle_portal'), HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {})

    def test_subscription_plan_info_requires_active_subscription(self):
        response = self.client.post(reverse('subscription_plan_info'), HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'success': False, 'error': 'No active subscription found'})


@override_settings(TB_PRO_SEND_API_URL='https://send-backend.example.org/', TB_PRO_SEND_API_KEY='test-key')
class SendStorageInfoViewTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.plan = Plan.objects.create(name='Test Plan', send_storage_bytes=10_000_000)
        self.user = User.objects.create(
            username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='sub/1234', plan=self.plan
        )
        Subscription.objects.create(
            paddle_id='sub_1234',
            paddle_customer_id='cus_1234',
            status=Subscription.StatusValues.ACTIVE,
            user=self.user,
        )
        oidc_force_login(self.client, self.user)
        self.url = reverse('subscription_send_storage')

    def _mock_response(self, status_code=200, data=None):
        response = MagicMock()
        response.status_code = status_code
        response.ok = 200 <= status_code < 400
        response.json.return_value = data
        return response

    def test_requires_active_subscription(self):
        Subscription.objects.filter(user=self.user).delete()

        response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'success': False, 'error': 'No active subscription found'})

    def test_returns_send_storage_usage(self):
        with patch(
            'thunderbird_accounts.subscription.send_client.requests.get',
            return_value=self._mock_response(data={'active': 1234, 'limit': 5678}),
        ) as get_mock:
            response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True, 'sendStorage': {'used': 1234, 'total': 5678}})

        # The subject is url-encoded and the integration key is sent as a bearer token
        args, kwargs = get_mock.call_args
        self.assertEqual(args[0], 'https://send-backend.example.org/api/internal/users/sub%2F1234/storage')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')

    def test_user_not_found_on_send_falls_back_to_plan_limit(self):
        with patch(
            'thunderbird_accounts.subscription.send_client.requests.get',
            return_value=self._mock_response(status_code=404),
        ):
            response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True, 'sendStorage': {'used': 0, 'total': 10_000_000}})

    def test_send_error_response(self):
        with patch(
            'thunderbird_accounts.subscription.send_client.requests.get',
            return_value=self._mock_response(status_code=503),
        ):
            response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {'success': False, 'error': 'Error getting Send storage usage'})

    def test_send_connection_error(self):
        with patch(
            'thunderbird_accounts.subscription.send_client.requests.get',
            side_effect=requests.ConnectionError('boom'),
        ):
            response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 502)

    def test_send_malformed_response(self):
        with patch(
            'thunderbird_accounts.subscription.send_client.requests.get',
            return_value=self._mock_response(data={'unexpected': True}),
        ):
            response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 502)

    @override_settings(TB_PRO_SEND_API_KEY='')
    def test_send_api_not_configured(self):
        with patch('thunderbird_accounts.subscription.send_client.requests.get') as get_mock:
            response = self.client.post(self.url, HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 503)
        get_mock.assert_not_called()
