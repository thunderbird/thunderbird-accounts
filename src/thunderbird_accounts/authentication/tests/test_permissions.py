import logging
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook


class IsValidPaddleWebhookTestCase(SimpleTestCase):
    expected_rejections = (
        "Unable to extract the 'Paddle-Signature' header from the request",
        'Too much time has elapsed between the request and this process',
    )

    @override_settings(PADDLE_WEBHOOK_KEY='test-secret')
    def test_expected_verification_rejections_are_logged_at_info_and_rejected(self):
        for message in self.expected_rejections:
            with self.subTest(message=message):
                request = SimpleNamespace(headers={}, body=b'{}')
                if message.startswith('Too much'):
                    request.headers['Paddle-Signature'] = 'ts=0;h1=unused'

                with self.assertLogs('paddle_billing', level='INFO') as logs:
                    self.assertIsNone(IsValidPaddleWebhook().authenticate(request))

                record = next(record for record in logs.records if record.getMessage() == message)
                self.assertEqual(record.levelno, logging.INFO)

    def test_unexpected_paddle_critical_log_remains_critical(self):
        message = 'Unexpected Paddle verification failure'

        with self.assertLogs('paddle_billing', level='INFO') as logs:
            logging.getLogger('paddle_billing').critical(message)

        record = next(record for record in logs.records if record.getMessage() == message)
        self.assertEqual(record.levelno, logging.CRITICAL)
