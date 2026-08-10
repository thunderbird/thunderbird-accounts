from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook


class IsValidPaddleWebhookTestCase(SimpleTestCase):
    expected_rejections = (
        "Unable to extract the 'Paddle-Signature' header from the request",
        'Too much time has elapsed between the request and this process',
    )

    def test_expected_verification_rejections_are_logged_and_rejected(self):
        for message in self.expected_rejections:
            with self.subTest(message=message):
                verifier = Mock()
                verifier.return_value.verify.side_effect = Exception(message)

                with (
                    patch('thunderbird_accounts.authentication.permissions.Verifier', verifier),
                    patch('thunderbird_accounts.authentication.permissions.Secret'),
                    patch('thunderbird_accounts.authentication.permissions.logging.info') as mock_info,
                ):
                    result = None
                    try:
                        result = IsValidPaddleWebhook().authenticate(Mock())
                    except Exception as exception:
                        self.fail(f'Expected Paddle rejection propagated: {exception}')

                self.assertIsNone(result)
                mock_info.assert_called_once_with(message)

    def test_unexpected_verification_rejection_propagates(self):
        verifier = Mock()
        verifier.return_value.verify.side_effect = Exception('Unexpected Paddle verification failure')

        with (
            patch('thunderbird_accounts.authentication.permissions.Verifier', verifier),
            patch('thunderbird_accounts.authentication.permissions.Secret'),
            patch('thunderbird_accounts.authentication.permissions.logging.info') as mock_info,
            self.assertRaisesRegex(Exception, 'Unexpected Paddle verification failure'),
        ):
            IsValidPaddleWebhook().authenticate(Mock())

        mock_info.assert_not_called()
