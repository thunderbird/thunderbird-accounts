import json
import datetime
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from thunderbird_accounts.subscription import tasks, models


class TransactionCreatedTaskTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # Make sure tasks run in sync
        settings.CELERY_TASK_ALWAYS_EAGER = True

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

        task_results: dict | None = tasks.paddle_transaction_created.delay(event_data, occurred_at).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))

        # Success results have model_created and model_uuid, so test this first
        self.assertEqual(task_results.get('task_status'), 'success')

        # This should be a new model
        self.assertTrue(task_results.get('model_created'))

        # Check if the model actually exists
        self.assertTrue(models.Transaction.objects.filter(pk=task_results.get('model_uuid')).exists())

    def test_out_of_date_webhook(self):
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

        task_results: dict | None = tasks.paddle_transaction_created.delay(event_data, occurred_at).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'webhook is out of date')

    def test_details_doesnt_exist(self):
        self.assertEqual(models.Transaction.objects.count(), 0)

        data = self.retrieve_webhook_fixture()
        event_data: dict = data.get('data')
        occurred_at: datetime.datetime = datetime.datetime.fromisoformat(data.get('occurred_at'))

        event_data.pop('details', '')

        task_results: dict | None = tasks.paddle_transaction_created.delay(event_data, occurred_at).get(timeout=10)

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

        task_results: dict | None = tasks.paddle_transaction_created.delay(event_data, occurred_at).get(timeout=10)

        self.assertIsNotNone(task_results)
        self.assertEqual(task_results.get('paddle_id'), event_data.get('id'))
        self.assertEqual(task_results.get('task_status'), 'failed')
        self.assertEqual(task_results.get('reason'), 'invalid total, tax, or currency strings')
