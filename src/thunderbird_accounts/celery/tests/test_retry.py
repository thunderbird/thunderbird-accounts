import requests
from django.test import SimpleTestCase

from thunderbird_accounts.celery.retry import is_retryable_external_service_error


class RetryableExternalServiceErrorTestCase(SimpleTestCase):
    def test_retries_transient_responses(self):
        for status_code in (429, 500, 502, 503, 504):
            response = requests.Response()
            response.status_code = status_code

            with self.subTest(status_code=status_code):
                self.assertTrue(is_retryable_external_service_error(requests.HTTPError(response=response)))

        self.assertTrue(is_retryable_external_service_error(requests.ConnectionError()))
        self.assertTrue(is_retryable_external_service_error(requests.Timeout()))

    def test_does_not_retry_permanent_responses(self):
        response = requests.Response()
        response.status_code = 400

        self.assertFalse(is_retryable_external_service_error(requests.HTTPError(response=response)))
