import json
import datetime
from pathlib import Path
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase as DRF_APITestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.subscription import tasks, models
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour


class PaddleWebhookViewTestCase(DRF_APITestCase):
    def setUp(self):
        self.client = APIClient()

    def skip_permission(self, _request):
        return User(), None

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_empty_webhook(self):
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()):
            with self.assertRaises(UnexpectedBehaviour) as ex:
                self.client.post('http://testserver/api/v1/subscription/paddle/webhook')
                self.assertEqual(ex.message, 'Paddle webhook is empty')

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_empty_occurred_at(self):
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()):
            with self.assertRaises(UnexpectedBehaviour) as ex:
                self.client.post(
                    'http://testserver/api/v1/subscription/paddle/webhook',
                    {
                        'event_type': 'transaction.created',
                        'event_data': {'not': 'empty'},
                    },
                    content_type='application/json',
                )
                self.assertEqual(ex.message, 'Paddle webhook is missing occurred at')

    @patch('thunderbird_accounts.authentication.permissions.IsValidPaddleWebhook.authenticate', skip_permission)
    def test_success(self):
        with patch('thunderbird_accounts.subscription.tasks.paddle_transaction_event', Mock()) as tx_created_mock:
            response = self.client.post(
                'http://testserver/api/v1/subscription/paddle/webhook',
                {
                    'event_type': 'transaction.created',
                    'event_data': {'not': 'empty'},
                    'occurred_at': '2024-04-12T10:18:49.621022Z',
                },
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            tx_created_mock.delay.assert_called()


class TransactionCreatedTaskTestCase(TestCase):
    is_create_event: bool = True
    celery_task_always_eager_setting: bool = False

    def setUp(self):
        super().setUp()

        self.celery_task_always_eager_setting = settings.CELERY_TASK_ALWAYS_EAGER

        # Make sure tasks run in sync
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        super().tearDown()

        settings.CELERY_TASK_ALWAYS_EAGER = self.celery_task_always_eager_setting

    def retrieve_webhook_fixture(self) -> dict:
        # Retrieve the webhook sample
        fixture_path = Path(__file__).parent.joinpath('fixtures/webhook_paddle_transaction_created.json')
        with open(fixture_path, 'r') as fh:
            data = json.loads(fh.read())
        return data

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

    def test_transaction_already_exists_or_out_of_date(self):
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

    def retrieve_webhook_fixture(self) -> dict:
        # Retrieve the webhook sample
        fixture_path = Path(__file__).parent.joinpath('fixtures/webhook_paddle_transaction_updated.json')
        with open(fixture_path, 'r') as fh:
            data = json.loads(fh.read())
        return data

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

    def test_transaction_already_exists_or_out_of_date(self):
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
