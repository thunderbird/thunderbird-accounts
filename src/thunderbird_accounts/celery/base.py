from celery.contrib.django.task import DjangoTask
from django.conf import settings
from django.db import OperationalError

from thunderbird_accounts.celery.exceptions import RetryableExternalServiceError


class DatabaseTask(DjangoTask):
    """Celery task base that retries transient database failures."""

    autoretry_for = (OperationalError,)
    retry_backoff = True
    retry_backoff_max = settings.CELERY_DATABASE_TASK_RETRY_BACKOFF_MAX
    retry_jitter = True
    max_retries = 8


class PatientExternalServiceTask(DatabaseTask):
    """Task base for durable background work against external services."""

    autoretry_for = DatabaseTask.autoretry_for + (RetryableExternalServiceError,)
    retry_backoff_max = settings.CELERY_PATIENT_TASK_RETRY_BACKOFF_MAX
    max_retries = settings.CELERY_PATIENT_TASK_MAX_RETRIES
