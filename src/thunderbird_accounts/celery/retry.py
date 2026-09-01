from functools import wraps

import requests

from thunderbird_accounts.celery.exceptions import RetryableExternalServiceError

TRANSIENT_EXTERNAL_SERVICE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable_external_service_error(exc: requests.RequestException) -> bool:
    """Return whether a request failure is likely to succeed later."""
    response = getattr(exc, 'response', None)
    if response is not None:
        return response.status_code in TRANSIENT_EXTERNAL_SERVICE_STATUS_CODES

    return isinstance(exc, (requests.ConnectionError, requests.Timeout))


def raise_retryable_external_service_error(exc: requests.RequestException) -> None:
    """Translate a transient request failure for patient Celery tasks."""
    if is_retryable_external_service_error(exc):
        raise RetryableExternalServiceError(str(exc)) from exc


def retry_transient_external_service_errors(func):
    """Translate transient request failures raised by a task body."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.RequestException as exc:
            raise_retryable_external_service_error(exc)
            raise

    return wrapped
