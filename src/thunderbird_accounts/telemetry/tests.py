from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from thunderbird_accounts.telemetry import capture, _get_client

import thunderbird_accounts.telemetry as telemetry_module


class GetClientTestCase(TestCase):
    def setUp(self):
        telemetry_module._client = None

    def tearDown(self):
        telemetry_module._client = None

    @override_settings(POSTHOG_API_KEY='', POSTHOG_HOST='')
    def test_returns_none_when_no_api_key(self):
        self.assertIsNone(_get_client())

    @patch('thunderbird_accounts.telemetry.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test123', POSTHOG_HOST='https://ph.test')
    def test_returns_singleton(self, mock_posthog_class):
        """Multiple calls return the same instance without re-initializing."""
        client1 = _get_client()
        client2 = _get_client()
        self.assertIs(client1, client2)
        mock_posthog_class.assert_called_once()


class CapturePrivacyTestCase(TestCase):
    """Tests that enforce privacy contracts: PII must never reach PostHog."""

    def setUp(self):
        telemetry_module._client = None

    def tearDown(self):
        telemetry_module._client = None

    @override_settings(POSTHOG_API_KEY='')
    def test_noop_when_not_configured(self):
        """Must not raise when PostHog is unconfigured."""
        capture(event='test.event', keycloak_user_id='some-uuid')

    @patch('thunderbird_accounts.telemetry.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    @patch.dict('os.environ', {'APP_ENV': 'prod'})
    def test_raw_user_id_never_used_as_distinct_id(self, mock_posthog_class):
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        raw_uuid = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'
        capture(event='accounts.login', keycloak_user_id=raw_uuid)

        call_kwargs = mock_client.capture.call_args.kwargs
        self.assertNotEqual(call_kwargs['distinct_id'], raw_uuid)
        self.assertEqual(len(call_kwargs['distinct_id']), 64)  # SHA-256 hex length

    @patch('thunderbird_accounts.telemetry.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    @patch.dict('os.environ', {'APP_ENV': 'test'})
    def test_empty_user_id_is_dropped(self, mock_posthog_class):
        """Events with no keycloak_user_id must not be submitted."""
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        capture(event='accounts.activity', keycloak_user_id='')
        capture(event='accounts.activity', keycloak_user_id=None)

        mock_client.capture.assert_not_called()

