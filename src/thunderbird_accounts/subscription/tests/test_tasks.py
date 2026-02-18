from thunderbird_accounts.celery.exceptions import TaskFailed
import requests
import json
import datetime
import hashlib
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from django.conf import settings
from django.core.signing import Signer
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APITestCase as DRF_APITestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.subscription import tasks, models
from thunderbird_accounts.mail import models as mail_models
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour
from thunderbird_accounts.utils.tests.utils import (
    build_keycloak_success_response,
    build_mail_get_account,
    build_mail_update_account,
)


class PaddleWebhookViewTestCase(DRF_APITestCase):
    """Test the actual webhook route"""

    def setUp(self):
        self.client = APIClient()

    def skip_permission(self, _request):
        return User(), None

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_empty_webhook(self):
        """Ensure a webhook that doesn't have any POST data errors out with an unexpected behaviour error."""
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()):
            with self.assertRaises(UnexpectedBehaviour) as ex:
                self.client.post('http://testserver/api/v1/subscription/paddle/webhook/')
                self.assertEqual(ex.message, 'Paddle webhook is empty')

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_empty_occurred_at(self):
        """Ensure a webhook will raise an unexpected behaviour error if there's occurred at."""
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()):
            with self.assertRaises(UnexpectedBehaviour) as ex:
                self.client.post(
                    'http://testserver/api/v1/subscription/paddle/webhook/',
                    {
                        'event_type': 'transaction.created',
                        'data': {'status': 'completed'},
                    },
                    content_type='application/json',
                )
                self.assertEqual(ex.message, 'Paddle webhook is missing occurred at')

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_success(self):
        """Test the minimum amount of data needed to be passed to celery."""

        event_types = [
            (
                'thunderbird_accounts.subscription.tasks.paddle_transaction_event',
                {
                    'event_type': 'transaction.created',
                    'data': {'status': 'completed'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
            ),
            (
                'thunderbird_accounts.subscription.tasks.paddle_transaction_event',
                {
                    'event_type': 'transaction.updated',
                    'data': {'status': 'completed'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
            ),
            (
                'thunderbird_accounts.subscription.tasks.paddle_subscription_event',
                {
                    'event_type': 'subscription.created',
                    'data': {'status': 'completed'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
            ),
            (
                'thunderbird_accounts.subscription.tasks.paddle_subscription_event',
                {
                    'event_type': 'subscription.updated',
                    'data': {'status': 'completed'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
            ),
            (
                'thunderbird_accounts.subscription.tasks.paddle_product_event',
                {
                    'event_type': 'product.created',
                    'data': {'name': 'hello world'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
            ),
            (
                'thunderbird_accounts.subscription.tasks.paddle_product_event',
                {
                    'event_type': 'product.updated',
                    'data': {'name': 'hello world'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
            ),
        ]

        for paddle_event, event_data in event_types:
            with patch(paddle_event, Mock()) as event_mock:
                response = self.client.post(
                    'http://testserver/api/v1/subscription/paddle/webhook/',
                    event_data,
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 200)
                event_mock.delay.assert_called()

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_draft_transactions_are_ignored(self):
        """Since this transaction.created event is a draft we ignore it."""
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()) as tx_created_mock:
            response = self.client.post(
                'http://testserver/api/v1/subscription/paddle/webhook/',
                {
                    'event_type': 'transaction.created',
                    'data': {'status': 'draft'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            tx_created_mock.delay.assert_not_called()

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_draft_transactions_arent_ignored_if_they_are_updated(self):
        """While we ignore transaction.created with the status of draft, we shouldn't ignore the unlikely
        but possible scenario that a transaction updates to a draft."""
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()) as tx_created_mock:
            response = self.client.post(
                'http://testserver/api/v1/subscription/paddle/webhook/',
                {
                    'event_type': 'transaction.updated',
                    'data': {'status': 'draft'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            tx_created_mock.delay.assert_called()


class PaddleTestCase(TestCase):
    """Base class for Paddle/Celery task unit tests."""

    celery_task_always_eager_setting: bool = False
    paddle_fixture = None
    test_user: User

    def setUp(self):
        super().setUp()

        self.celery_task_always_eager_setting = settings.CELERY_TASK_ALWAYS_EAGER
        self.test_user = User.objects.create_user('test@example.org', 'test@example.org', '1234')

        # Create a mail account
        self.test_mail_account = Account.objects.create(
            name='Test Account',
            user_id=self.test_user.uuid,
        )

        # If required we need to attach a fake product and plan to this test
        data = self.retrieve_webhook_fixture()
        if data:
            event_data: dict = data.get('data')
            for item in event_data.get('items', []):
                product_data: dict = item.get('product')
                if product_data:
                    product, _created = models.Product.objects.update_or_create(
                        paddle_id=product_data.get('id'),
                        defaults={
                            'paddle_id': product_data.get('id'),
                            'name': product_data.get('name'),
                            'product_type': product_data.get('type'),
                            'status': models.Product.StatusValues.ACTIVE.value,
                        },
                    )
                    self.assertIsNotNone(product)
                    plan, _created = models.Plan.objects.update_or_create(
                        name=f'{product_data.get("name")} plan',
                        defaults={
                            'visible_on_subscription_page': True,
                            'product': product,
                        },
                    )
                    self.assertIsNotNone(plan)

        # Make sure tasks run in sync
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        super().tearDown()

        settings.CELERY_TASK_ALWAYS_EAGER = self.celery_task_always_eager_setting

    def retrieve_webhook_fixture(self) -> dict:
        # Retrieve the webhook sample
        if self.paddle_fixture is None:
            raise ValueError

        fixture_path = Path(__file__).parent.joinpath(self.paddle_fixture)
        with open(fixture_path, 'r') as fh:
            data = json.loads(fh.read())
        return data


class TransactionCreatedTaskTestCase(PaddleTestCase):
    is_create_event: bool = True
    paddle_fixture = 'fixtures/webhook_paddle_transaction_created.json'

    def test_success(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        task_results: dict | None = tasks.paddle_transaction_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success')

        # This should be a new model
        self.assertTrue(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Transaction.objects.filter(pk=task_results.get('model_uuid')).exists())

    def test_transaction_already_exists(self):
        """We're testing if the transaction already exists here."""
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        transaction = models.Transaction.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
            total='0',
            tax='0',
            currency='CAD',
        )

        self.assertIsNotNone(transaction)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_transaction_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'transaction already exists')

    def test_details_doesnt_exist(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        data = self.retrieve_webhook_fixture()
        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        event_data.pop('details', '')

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_transaction_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'no details or totals object')

    def test_totals_is_bad(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        data = self.retrieve_webhook_fixture()
        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        # Remove the keys
        del event_data['details']['totals']['total']
        del event_data['details']['totals']['tax']
        del event_data['details']['totals']['currency_code']

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_transaction_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'invalid total, tax, or currency strings')


class TransactionUpdatedTaskTestCase(TransactionCreatedTaskTestCase):
    is_create_event: bool = False
    paddle_fixture = 'fixtures/webhook_paddle_transaction_updated.json'

    def test_success(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        # An initial transaction we'll update
        transaction = models.Transaction.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
            total='0',
            tax='0',
            currency='CAD',
        )

        task_results: dict | None = tasks.paddle_transaction_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success')

        # This should be a new model
        self.assertFalse(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Transaction.objects.filter(pk=task_results.get('model_uuid')).exists())

        self.assertEqual(task_results.get('model_uuid'), transaction.uuid)

        # Refresh the transaction now that we've updated it
        transaction.refresh_from_db()

        self.assertNotEqual(transaction.total, '0')
        self.assertNotEqual(transaction.tax, '0')

        self.assertEqual(transaction.total, event_data.get('details', {}).get('totals', {}).get('total'))
        self.assertEqual(transaction.tax, event_data.get('details', {}).get('totals', {}).get('tax'))
        self.assertEqual(transaction.currency, event_data.get('details', {}).get('totals', {}).get('currency_code'))

    def test_transaction_already_exists(self):
        """This isn't needed in context of TransactionUpdated, but we inherit it so we need to stub it out."""
        pass

    def test_transaction_out_of_date(self):
        """We're testing if the transaction is out of date here."""
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        transaction = models.Transaction.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at + datetime.timedelta(hours=1),
            total='0',
            tax='0',
            currency='CAD',
        )

        self.assertIsNotNone(transaction)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_transaction_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'webhook is out of date')


class SubscriptionCreatedTaskTestCase(PaddleTestCase):
    is_create_event: bool = True
    paddle_fixture = 'fixtures/webhook_paddle_subscription_created.json'

    def retrieve_webhook_fixture(self) -> dict:
        event_data = super().retrieve_webhook_fixture()

        # We perform this operation via paddle.js's checkout flow
        # so we'll need it in the incoming webhook data.
        signer = Signer()
        event_data['data']['custom_data'] = {'signed_user_id': signer.sign(self.test_user.uuid.hex)}

        return event_data

    @patch('thunderbird_accounts.mail.clients.MailClient._get_principal')
    @patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
    def test_success(self, mock_request, mail_client):
        mock_request.return_value = build_keycloak_success_response()
        mail_client.return_value = build_mail_get_account()

        self.assertEqual(models.Subscription.objects.count(), 0)

        # Ensure they're in the payment pending state
        self.test_user.is_awaiting_payment_verification = True
        self.test_user.save()

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success', msg=task_results)

        # This should be a new model
        self.assertTrue(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Subscription.objects.filter(pk=task_results.get('model_uuid')).exists())

        subscription = models.Subscription.objects.filter(pk=task_results.get('model_uuid')).get()

        # Check if the model is associated with the test user
        self.assertIsNotNone(subscription.user_id)
        self.assertIsNotNone(subscription.user)
        self.assertEqual(subscription.user_id, self.test_user.uuid)
        self.assertEqual(subscription.user.uuid, self.test_user.uuid)

        # Check for a related transaction
        self.assertTrue(models.Transaction.objects.count() > 0)
        self.assertTrue(models.Transaction.objects.filter(subscription_id=subscription.uuid).exists())

        # Check for subscription items - Test data has 2!
        self.assertTrue(subscription.subscriptionitem_set.count() == 2)

        subscription_items = subscription.subscriptionitem_set.all()
        self.assertEqual(subscription_items[0].paddle_price_id, 'pri_01gsz8x8sawmvhz1pv30nge1ke')
        self.assertEqual(subscription_items[0].paddle_product_id, 'pro_01gsz4t5hdjse780zja8vvr7jg')
        self.assertEqual(subscription_items[0].paddle_subscription_id, subscription.paddle_id)
        self.assertEqual(subscription_items[0].quantity, 10)
        self.assertIsNotNone(subscription_items[0].subscription)
        self.assertIsNotNone(subscription_items[0].price)

        self.assertEqual(subscription_items[1].paddle_price_id, 'pri_01h1vjfevh5etwq3rb416a23h2')
        self.assertEqual(subscription_items[1].paddle_product_id, 'pro_01h1vjes1y163xfj1rh1tkfb65')
        self.assertEqual(subscription_items[1].paddle_subscription_id, subscription.paddle_id)
        self.assertEqual(subscription_items[1].quantity, 1)
        self.assertIsNotNone(subscription_items[1].subscription)
        self.assertIsNotNone(subscription_items[1].price)

        # Refresh the user
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_awaiting_payment_verification)
        self.assertIsNotNone(self.test_user.plan)

    @patch('thunderbird_accounts.mail.clients.MailClient._get_principal')
    @patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
    def test_success_updates_account_quota(self, mock_request, mail_client):
        mock_request.return_value = build_keycloak_success_response()
        mail_client.return_value = build_mail_get_account()

        self.assertEqual(models.Subscription.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        items = event_data.get('items')
        self.assertIsNotNone(items)

        product_id = items[0].get('product', {}).get('id')
        product_name = items[0].get('product', {}).get('name')

        self.assertIsNotNone(product_id)
        self.assertIsNotNone(product_name)

        # Created in base class setup
        product = models.Product.objects.get(paddle_id=product_id)

        self.assertIsNotNone(product)

        quota_in_bytes = 1337 * settings.ONE_GIGABYTE_IN_BYTES

        plan = product.plan
        plan.mail_storage_bytes = quota_in_bytes
        plan.save()

        self.assertIsNotNone(plan)

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success', msg=task_results)

        # This should be a new model
        self.assertTrue(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Subscription.objects.filter(pk=task_results.get('model_uuid')).exists())

    def test_subscription_already_exists(self):
        self.assertEqual(models.Subscription.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        subscription = models.Subscription.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
        )

        self.assertIsNotNone(subscription)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_subscription_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)

        task_results = ex.exception.other
        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'subscription already exists')

    def test_subscription_error_no_signed_user_id(self):
        self.assertEqual(models.Subscription.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        event_data['custom_data'] = None

        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        task_results = {}
        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_subscription_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'no signed user id provided')


class SubscriptionUpdatedTaskTestCase(SubscriptionCreatedTaskTestCase):
    is_create_event: bool = False
    paddle_fixture = 'fixtures/webhook_paddle_subscription_updated.json'

    @patch('thunderbird_accounts.mail.clients.MailClient._get_principal')
    @patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
    def test_success(self, mock_request, mail_client):
        mock_request.return_value = build_keycloak_success_response()
        mail_client.return_value = build_mail_get_account()
        self.assertEqual(models.Subscription.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        subscription = models.Subscription.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
        )

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), subscription.paddle_id)

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success', msg=task_results)

        # This should be a new model
        self.assertFalse(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Subscription.objects.filter(pk=task_results.get('model_uuid')).exists())

        subscription.refresh_from_db()

        # Spot check some updated fields
        self.assertEqual(event_data.get('status'), subscription.status)
        self.assertEqual(event_data.get('customer_id'), subscription.paddle_customer_id)

        # Check if the model is associated with the test user
        self.assertIsNotNone(subscription.user_id)
        self.assertIsNotNone(subscription.user)
        self.assertEqual(subscription.user_id, self.test_user.uuid)
        self.assertEqual(subscription.user.uuid, self.test_user.uuid)

        # Update does not create transaction_id
        self.assertTrue(models.Transaction.objects.count() == 0)

        # Check for subscription items - Test data has 3!
        self.assertTrue(subscription.subscriptionitem_set.count() == 3)

        subscription_items = subscription.subscriptionitem_set.all()
        self.assertEqual(subscription_items[0].paddle_price_id, 'pri_01gsz8x8sawmvhz1pv30nge1ke')
        self.assertEqual(subscription_items[0].paddle_product_id, 'pro_01gsz4t5hdjse780zja8vvr7jg')
        self.assertEqual(subscription_items[0].paddle_subscription_id, subscription.paddle_id)
        self.assertEqual(subscription_items[0].quantity, 20)  # Updated!
        self.assertIsNotNone(subscription_items[0].subscription)
        self.assertIsNotNone(subscription_items[0].price)

        self.assertEqual(subscription_items[1].paddle_price_id, 'pri_01h1vjfevh5etwq3rb416a23h2')
        self.assertEqual(subscription_items[1].paddle_product_id, 'pro_01h1vjes1y163xfj1rh1tkfb65')
        self.assertEqual(subscription_items[1].paddle_subscription_id, subscription.paddle_id)
        self.assertEqual(subscription_items[1].quantity, 1)
        self.assertIsNotNone(subscription_items[1].subscription)
        self.assertIsNotNone(subscription_items[1].price)

        # New!
        self.assertEqual(subscription_items[2].paddle_price_id, 'pri_01gsz95g2zrkagg294kpstx54r')
        self.assertEqual(subscription_items[2].paddle_product_id, 'pro_01gsz92krfzy3hcx5h5rtgnfwz')
        self.assertEqual(subscription_items[2].paddle_subscription_id, subscription.paddle_id)
        self.assertEqual(subscription_items[2].quantity, 1)
        self.assertIsNotNone(subscription_items[2].subscription)
        self.assertIsNotNone(subscription_items[2].price)

    def test_subscription_already_exists(self):
        """Not needed for update webhook"""
        pass

    def test_subscription_out_of_date(self):
        """We're testing if the transaction is out of date here."""
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        subscription = models.Subscription.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at + datetime.timedelta(hours=1),
        )

        self.assertIsNotNone(subscription)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_subscription_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)

        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'webhook is out of date')


class SubscriptionUpdatedToCancelledTaskTestCase(SubscriptionCreatedTaskTestCase):
    is_create_event: bool = False
    paddle_fixture = 'fixtures/webhook_paddle_subscription_cancelled.json'

    def test_success(self):
        self.assertEqual(models.Subscription.objects.count(), 0)

        self.test_user.is_awaiting_payment_verification = True
        self.test_user.save()

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        subscription = models.Subscription.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
        )

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), subscription.paddle_id)

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success', msg=task_results)

        # This should be a new model
        self.assertFalse(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Subscription.objects.filter(pk=task_results.get('model_uuid')).exists())

        subscription.refresh_from_db()

        # Spot check some updated fields
        self.assertEqual(event_data.get('status'), subscription.status)
        self.assertEqual(event_data.get('customer_id'), subscription.paddle_customer_id)

        # Check if the model is associated with the test user
        self.assertIsNotNone(subscription.user_id)
        self.assertIsNotNone(subscription.user)
        self.assertEqual(subscription.user_id, self.test_user.uuid)
        self.assertEqual(subscription.user.uuid, self.test_user.uuid)

        # Update does not create transaction_id
        self.assertTrue(models.Transaction.objects.count() == 0)

        # Check for subscription items - Test data has 1!
        self.assertTrue(subscription.subscriptionitem_set.count() == 1)

        self.assertTrue(subscription.status == models.Subscription.StatusValues.CANCELED.value)

        # Refresh the test user, and confirm that the payment pending flag was not cleared (as this is a cancel)
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_awaiting_payment_verification)

    def test_subscription_already_exists(self):
        """Not needed for update webhook"""
        pass

    def test_subscription_out_of_date(self):
        """We're testing if the transaction is out of date here."""
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        subscription = models.Subscription.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at + datetime.timedelta(hours=1),
        )

        self.assertIsNotNone(subscription)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_subscription_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'webhook is out of date')


class ProductCreatedTaskTestCase(PaddleTestCase):
    is_create_event: bool = True
    paddle_fixture = 'fixtures/webhook_paddle_product_created.json'

    def test_success(self):
        self.assertEqual(models.Product.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        task_results: dict | None = tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(
            timeout=10
        )

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success')

        # This should be a new model
        self.assertTrue(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Product.objects.filter(pk=task_results.get('model_uuid')).exists())

    def test_already_exists(self):
        """We're testing if the transaction already exists here."""
        self.assertEqual(models.Product.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        product = models.Product.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
            name='A product',
            product_type=models.Product.TypeValues.STANDARD,
            status=models.Product.StatusValues.ACTIVE,
        )

        self.assertIsNotNone(product)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'product already exists')


class ProductUpdatedTaskTestCase(ProductCreatedTaskTestCase):
    is_create_event: bool = False
    paddle_fixture = 'fixtures/webhook_paddle_product_updated.json'

    def test_success(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        # An initial transaction we'll update
        product = models.Product.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at - datetime.timedelta(hours=1),
            name='A product',
            product_type=models.Product.TypeValues.STANDARD,
            status=models.Product.StatusValues.ACTIVE,
        )

        task_results = tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success')

        # This should be a new model
        self.assertFalse(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Product.objects.filter(pk=task_results.get('model_uuid')).exists())

        self.assertEqual(task_results.get('model_uuid'), product.uuid)

        # Refresh the transaction now that we've updated it
        product.refresh_from_db()

        self.assertEqual(product.name, event_data.get('name'))
        self.assertEqual(product.description, event_data.get('description'))
        self.assertEqual(product.status, event_data.get('status'))
        self.assertEqual(product.product_type, event_data.get('type'))

    def test_already_exists(self):
        """This isn't needed in context of ProductUpdated, but we inherit it so we need to stub it out."""
        pass

    def test_out_of_date(self):
        """We're testing if the transaction is out of date here."""
        self.assertEqual(models.Product.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        product = models.Product.objects.create(
            paddle_id=event_data.get('id'),
            webhook_updated_at=occurred_at + datetime.timedelta(hours=1),
            name='A product',
            product_type=models.Product.TypeValues.STANDARD,
            status=models.Product.StatusValues.ACTIVE,
        )

        self.assertIsNotNone(product)

        with self.assertRaises(TaskFailed) as ex:
            tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(ex.exception.reason, 'webhook is out of date')


class UpdateThundermailQuotaTestCase(TestCase):
    celery_task_always_eager_setting: bool = False
    test_user: User = None

    def setUp(self):
        super().setUp()

        self.celery_task_always_eager_setting = settings.CELERY_TASK_ALWAYS_EAGER
        self.test_user = User.objects.create_user('test', 'test@example.org', '1234')

        # Make sure tasks run in sync
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        super().tearDown()

        settings.CELERY_TASK_ALWAYS_EAGER = self.celery_task_always_eager_setting

    @patch('thunderbird_accounts.mail.clients.MailClient._get_principal')
    @patch('thunderbird_accounts.mail.clients.MailClient._update_principal')
    def test_success(self, update_mail_client, get_mail_client):
        update_mail_client.return_value = build_mail_update_account()
        get_mail_client.return_value = build_mail_get_account()

        # Create the paddle objects
        product = models.Product.objects.create(
            paddle_id='pro_123',
            name='A product',
            product_type=models.Product.TypeValues.STANDARD,
            status=models.Product.StatusValues.ACTIVE,
        )
        subscription = models.Subscription.objects.create(
            paddle_id='sub_123',
            user_id=self.test_user.uuid,
        )
        _subscription_item = models.SubscriptionItem.objects.create(
            quantity=1,
            subscription_id=subscription.uuid,
            product_id=product.uuid,
        )
        plan = models.Plan.objects.create(name='Test Plan', mail_storage_bytes=1, product_id=product.uuid)

        # Create the thundermail objects
        # ...Why mail models?
        mail_models.Account.objects.create(
            name='Test Account',
            user_id=self.test_user.uuid,
        )

        # Run the task
        task_results: dict | None = tasks.update_thundermail_quota.delay(plan_uuid=plan.uuid.hex).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('plan_uuid'), plan.uuid.hex)
        self.assertEqual(task_results.get('task_status'), 'success')
        self.assertEqual(task_results.get('updated'), 1)
        self.assertEqual(task_results.get('skipped'), 0)

    def test_plan_does_not_exist(self):
        # Manually created this uuid, it should not exist
        plan_uuid = '13371337-aaaa-bbbb-cccc-123456789abc'
        with self.assertRaises(models.Plan.DoesNotExist):
            models.Plan.objects.get(pk=plan_uuid)

        # Run the task
        with self.assertRaises(TaskFailed) as ex:
            tasks.update_thundermail_quota.delay(plan_uuid=plan_uuid).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('plan_uuid'), plan_uuid)
        self.assertEqual(ex.exception.reason, 'plan does not exist')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    MAILCHIMP_API_KEY='< intentionally blank >',
    MAILCHIMP_LIST_ID='< intentionally blank >',
    MAILCHIMP_DC='< intentionally blank >',
)
class AddSubscriberToMailchimpList(TestCase):
    test_user: User

    def setUp(self):
        super().setUp()

        self.test_user = User.objects.create_user('test@example.com', 'test@example.org', '1234')
        models.Subscription.objects.create(
            paddle_id='pad123',
            status=models.Subscription.StatusValues.ACTIVE.value,
            user=self.test_user,
        )
        account = Account.objects.create(
            name=self.test_user.username,
            user=self.test_user,
        )
        Email.objects.create(address=self.test_user.username, account=account, type=Email.EmailType.PRIMARY.value)

    def tearDown(self):
        super().tearDown()

    @patch('requests.request')
    def test_success_create(self, request_mock: MagicMock):
        """Ensure that given a subscribed user with a valid stalwart email that
        they will successfully be added to the mailchimp list"""
        get_member_response = requests.Response()
        get_member_response.status_code = 404

        create_member_response = requests.Response()
        create_member_response.status_code = 200

        request_mock.side_effect = [
            # Thundermail
            get_member_response,
            create_member_response,
            # Recovery Email
            get_member_response,
            create_member_response,
        ]

        task_results: dict | None = tasks.add_subscriber_to_mailchimp_list.delay(str(self.test_user.uuid)).get(
            timeout=10
        )

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('task_status'), 'success')
        self.assertEqual(task_results.get('user_uuid'), str(self.test_user.uuid))

        # We call it 4 times (2 for both emails)
        self.assertEqual(request_mock.call_count, 4)

        # Reverse order because of .pop()
        email_addresses = [self.test_user.email, self.test_user.stalwart_primary_email]
        for i in range(0, 4, 2):
            get_req = request_mock.call_args_list[i]
            update_tag_req = request_mock.call_args_list[i + 1]
            address_to_test = email_addresses.pop()

            md5_hasher = hashlib.new('md5')
            md5_hasher.update(address_to_test.lower().encode())
            hashed_email = md5_hasher.hexdigest()

            # Test the GET request and the POST (update tag) request
            self.assertIn(hashed_email, get_req[1]['url'])
            self.assertNotIn('/tags', update_tag_req[1]['url'])
            self.assertEqual(address_to_test, update_tag_req[1]['json']['email_address'])

    @patch('requests.request')
    def test_success_update(self, request_mock: MagicMock):
        """Ensure that given a subscribed user with a valid stalwart email that
        they will successfully have the proper tag added to their entry."""
        fake_response = requests.Response()
        fake_response.status_code = 200

        get_member_response = requests.Response()
        get_member_response.status_code = 200
        get_member_response._content = b'{}'

        update_member_tag = requests.Response()
        update_member_tag.status_code = 200

        request_mock.side_effect = [
            # Thundermail
            get_member_response,
            update_member_tag,
            # Recovery Email
            get_member_response,
            update_member_tag,
        ]

        task_results: dict | None = tasks.add_subscriber_to_mailchimp_list.delay(str(self.test_user.uuid)).get(
            timeout=10
        )

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('task_status'), 'success')
        self.assertEqual(task_results.get('user_uuid'), str(self.test_user.uuid))

        # We call it 4 times (2 for both emails)
        self.assertEqual(request_mock.call_count, 4)

        # Reverse order because of .pop()
        email_addresses = [self.test_user.email, self.test_user.stalwart_primary_email]
        tags = ['welcome', 'new_user']
        for i in range(0, 4, 2):
            get_req = request_mock.call_args_list[i]
            update_tag_req = request_mock.call_args_list[i + 1]
            address_to_test = email_addresses.pop()
            tag_to_test = tags.pop()

            md5_hasher = hashlib.new('md5')
            md5_hasher.update(address_to_test.lower().encode())
            hashed_email = md5_hasher.hexdigest()

            # Test the GET request and the POST (update tag) request
            self.assertIn(hashed_email, get_req[1]['url'])
            self.assertIn('/tags', update_tag_req[1]['url'])
            self.assertEqual([{'name': tag_to_test, 'status': 'active'}], update_tag_req[1]['json']['tags'])

    @patch('requests.request')
    def test_bad_user(self, request_mock: MagicMock):
        """Ensure that we catch users that do not exist."""
        fake_response = requests.Response()
        fake_response.status_code = 500

        bad_user_uuid = '4b6c15c9b2c94c9389de992f05d1441b'

        request_mock.return_value = fake_response

        with self.assertRaises(TaskFailed) as ex:
            tasks.add_subscriber_to_mailchimp_list.delay(bad_user_uuid).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('user_uuid'), bad_user_uuid)
        self.assertEqual(ex.exception.reason, 'user does not exist')

    @patch('requests.request')
    def test_user_not_subscribed(self, request_mock: MagicMock):
        """Ensure that we catch users who are not subscribed"""
        fake_response = requests.Response()
        fake_response.status_code = 500

        test_user = User.objects.create_user('test2@example.com', 'test2@example.org', '1234')

        request_mock.return_value = fake_response
        with self.assertRaises(TaskFailed) as ex:
            tasks.add_subscriber_to_mailchimp_list.delay(str(test_user.uuid)).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('user_uuid'), str(test_user.uuid))
        self.assertEqual(ex.exception.reason, 'user is not subscribed')

    @patch('requests.request')
    def test_bad_request(self, request_mock: MagicMock):
        """Ensure we catch bad requests from mailchimp"""
        fake_response = requests.Response()
        fake_response.status_code = 404

        request_mock.return_value = fake_response
        with self.assertRaises(TaskFailed) as ex:
            tasks.add_subscriber_to_mailchimp_list.delay(str(self.test_user.uuid)).get(timeout=10)
        task_results = ex.exception.other

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('user_uuid'), str(self.test_user.uuid))
        self.assertEqual(ex.exception.reason, 'mailchimp error')
