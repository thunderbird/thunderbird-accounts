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
