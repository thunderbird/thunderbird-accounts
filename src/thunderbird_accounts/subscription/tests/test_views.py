from thunderbird_accounts.subscription.models import Transaction
import json
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.utils.tests.utils import oidc_force_login


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

    @override_settings(IS_DEV=False)
    def test_transaction_found_and_is_doneish_by_being_paid(self):
        """We found the transaction but it's doneish (status=PAID). This should trigger payment verification
        and remove txid from session.

        We should also ensure IS_DEV=False does not call Paddle or the fake webhook task."""

        # Make sure we have a txid in session
        self.set_paddle_transaction_id()

        transaction = Transaction.objects.create(paddle_id=self.txid, status=Transaction.StatusValues.PAID.value)
        self.assertIsNotNone(transaction)

        with patch('thunderbird_accounts.subscription.tasks.dev_only_paddle_fake_webhook', MagicMock()) as task_mock:
            with patch('thunderbird_accounts.subscription.decorators.Client', MagicMock()) as paddle_client_mock:
                instance = paddle_client_mock()

                self.assertFalse(self.user.is_awaiting_payment_verification)

                response = self.client.post(
                    self.url,
                    follow=False,
                )
                self.assertTrue(response)
                self.assertEqual(response.status_code, 200)

                data = response.json()
                self.assertTrue(data)
                self.assertEqual(data.get('status'), Transaction.StatusValues.PAID.value)

                self.user.refresh_from_db()
                self.assertTrue(self.user.is_awaiting_payment_verification)

                instance.notifications.list.assert_not_called()
                task_mock.assert_not_called()
