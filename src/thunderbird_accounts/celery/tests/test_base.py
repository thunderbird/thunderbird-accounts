from unittest.mock import patch

from celery.exceptions import Retry
from django.conf import settings
from django.db import OperationalError
from django.test import SimpleTestCase

from thunderbird_accounts.celery import app
from thunderbird_accounts.celery.base import DatabaseTask, PatientExternalServiceTask
from thunderbird_accounts.celery.exceptions import RetryableExternalServiceError


@app.task(base=DatabaseTask)
def database_failure():
    raise OperationalError('database unavailable')


@app.task(base=DatabaseTask)
def non_database_failure():
    raise ValueError('invalid input')


@app.task(base=PatientExternalServiceTask)
def external_service_failure():
    raise RetryableExternalServiceError('service unavailable')


class DatabaseTaskTestCase(SimpleTestCase):
    def test_uses_configured_backoff_max(self):
        self.assertEqual(DatabaseTask.retry_backoff_max, settings.CELERY_DATABASE_TASK_RETRY_BACKOFF_MAX)

    def test_retries_operational_errors(self):
        with patch.object(database_failure, 'retry', side_effect=Retry()) as retry:
            with self.assertRaises(Retry):
                database_failure.run()

        self.assertIsInstance(retry.call_args.kwargs['exc'], OperationalError)

    def test_does_not_retry_other_errors(self):
        with self.assertRaises(ValueError):
            non_database_failure.run()

    def test_patiently_retries_external_service_errors(self):
        with patch.object(external_service_failure, 'retry', side_effect=Retry()) as retry:
            with self.assertRaises(Retry):
                external_service_failure.run()

        self.assertIsInstance(retry.call_args.kwargs['exc'], RetryableExternalServiceError)
