import json
import datetime
from pathlib import Path
from unittest.mock import patch, Mock

from django.conf import settings
from django.core.signing import Signer
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase as DRF_APITestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.subscription import tasks, models
from thunderbird_accounts.mail import models as mail_models
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour


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
        self.test_user = User.objects.create_user('test', 'test@example.org', '1234')

        # Create a mail account
        self.test_mail_account = Account.objects.create(
            name='Test Account',
            user_id=self.test_user.uuid,
        )

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

        task_results: dict | None = tasks.paddle_transaction_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'transaction already exists')

    def test_details_doesnt_exist(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        data = self.retrieve_webhook_fixture()
        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        event_data.pop('details', '')

        task_results: dict | None = tasks.paddle_transaction_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'no details or totals object')

    def test_totals_is_bad(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        data = self.retrieve_webhook_fixture()
        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        # Remove the keys
        del event_data['details']['totals']['total']
        del event_data['details']['totals']['tax']
        del event_data['details']['totals']['currency_code']

        task_results: dict | None = tasks.paddle_transaction_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'invalid total, tax, or currency strings')


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

        task_results: dict | None = tasks.paddle_transaction_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'webhook is out of date')


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

    def test_success(self):
        self.assertEqual(models.Subscription.objects.count(), 0)

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

    def test_success_updates_account_quota(self):
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

        product = models.Product.objects.create(paddle_id=product_id, name=product_name)

        self.assertIsNotNone(product)

        quota_in_gb = 1337
        plan = models.Plan.objects.create(
            name='Test Plan',
            product_id=product.uuid,
            mail_storage_gb=quota_in_gb,
        )

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

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'subscription already exists')

    def test_subscription_error_no_signed_user_id(self):
        self.assertEqual(models.Subscription.objects.count(), 0)

        # Retrieve the webhook sample
        data = self.retrieve_webhook_fixture()

        event_data: dict = data.get('data')
        event_data['custom_data'] = None

        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'no signed user id provided')


class SubscriptionUpdatedTaskTestCase(SubscriptionCreatedTaskTestCase):
    is_create_event: bool = False
    paddle_fixture = 'fixtures/webhook_paddle_subscription_updated.json'

    def test_success(self):
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

        task_results: dict | None = tasks.paddle_subscription_event.delay(
            event_data, occurred_at, self.is_create_event
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'webhook is out of date')


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

        task_results: dict | None = tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(
            timeout=10
        )

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'product already exists')


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

        task_results: dict | None = tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(
            timeout=10
        )

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

        task_results: dict | None = tasks.paddle_product_event.delay(event_data, occurred_at, self.is_create_event).get(
            timeout=10
        )

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'webhook is out of date')


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

    def test_success(self):
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
        plan = models.Plan.objects.create(name='Test Plan', mail_storage_gb=1, product_id=product.uuid)

        # Create the thundermail objects
        # ...Why mail models?
        mail_models.Account.objects.create(
            name='Test Account',
            user_id=self.test_user.uuid,
        )

        # Run the task
        task_results: dict | None = tasks.update_thundermail_quota.delay(
            plan_uuid=plan.uuid.hex, mail_storage_gb=plan.mail_storage_gb
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('plan_uuid'), plan.uuid.hex)
        self.assertEqual(task_results.get('mail_storage_gb'), plan.mail_storage_gb)
        self.assertEqual(task_results.get('task_status'), 'success')
        self.assertEqual(task_results.get('updated'), 1)
        self.assertEqual(task_results.get('skipped'), 0)

    def test_plan_does_not_exist(self):
        # Manually created this uuid, it should not exist
        plan_uuid = '13371337-aaaa-bbbb-cccc-123456789abc'
        storage = 1
        with self.assertRaises(models.Plan.DoesNotExist):
            models.Plan.objects.get(pk=plan_uuid)

        # Run the task
        task_results: dict | None = tasks.update_thundermail_quota.delay(
            plan_uuid=plan_uuid, mail_storage_gb=storage
        ).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('plan_uuid'), plan_uuid)
        self.assertEqual(task_results.get('mail_storage_gb'), storage)
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'plan does not exist')
