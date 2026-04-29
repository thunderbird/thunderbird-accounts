from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from thunderbird_accounts.telemetry.client import _get_client, capture, submit_event

import thunderbird_accounts.telemetry.client as telemetry_module


class GetClientTestCase(TestCase):
    def setUp(self):
        telemetry_module._make_client.cache_clear()

    def tearDown(self):
        telemetry_module._make_client.cache_clear()

    @override_settings(POSTHOG_API_KEY=None)
    def test_returns_none_when_no_api_key(self):
        self.assertIsNone(_get_client())

    @patch('thunderbird_accounts.telemetry.client.Posthog')
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
        telemetry_module._make_client.cache_clear()

    def tearDown(self):
        telemetry_module._make_client.cache_clear()

    @override_settings(POSTHOG_API_KEY=None)
    def test_noop_when_not_configured(self):
        """Must not raise when PostHog is unconfigured."""
        capture(event='test.event', keycloak_user_id='some-uuid')

    @patch('thunderbird_accounts.telemetry.client.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test', APP_ENV='prod')
    def test_raw_user_id_never_used_as_distinct_id(self, mock_posthog_class):
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        raw_uuid = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'
        capture(event='accounts.login', keycloak_user_id=raw_uuid)

        call_kwargs = mock_client.capture.call_args.kwargs
        self.assertNotEqual(call_kwargs['distinct_id'], raw_uuid)
        self.assertEqual(len(call_kwargs['distinct_id']), 64)  # SHA-256 hex length

    @patch('thunderbird_accounts.telemetry.client.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test', APP_ENV='test')
    def test_empty_user_id_is_dropped(self, mock_posthog_class):
        """Events with no keycloak_user_id must not be submitted."""
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        capture(event='accounts.activity', keycloak_user_id='')
        capture(event='accounts.activity', keycloak_user_id=None)

        mock_client.capture.assert_not_called()


class SubmitEventTimestampTestCase(TestCase):
    """submit_event must hand PostHog a real datetime; the SDK silently drops string timestamps."""

    def setUp(self):
        telemetry_module._make_client.cache_clear()

    def tearDown(self):
        telemetry_module._make_client.cache_clear()

    @patch('thunderbird_accounts.telemetry.client.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test', APP_ENV='test')
    def test_string_timestamp_is_parsed(self, mock_posthog_class):
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        cases = [
            ('2026-04-29T02:56:51Z', datetime(2026, 4, 29, 2, 56, 51, tzinfo=timezone.utc)),
            ('2026-04-29T02:56:51+02:00', datetime(2026, 4, 29, 2, 56, 51, tzinfo=timezone(timedelta(hours=2)))),
            ('2026-04-29T02:56:51-05:00', datetime(2026, 4, 29, 2, 56, 51, tzinfo=timezone(timedelta(hours=-5)))),
            ('2026-04-29T02:56:51.123456Z', datetime(2026, 4, 29, 2, 56, 51, 123456, tzinfo=timezone.utc)),
        ]
        for ts_in, expected in cases:
            with self.subTest(timestamp=ts_in):
                mock_client.reset_mock()
                submit_event(distinct_id='abc', event='thundermail.x', timestamp=ts_in)
                call_kwargs = mock_client.capture.call_args.kwargs
                self.assertIsInstance(call_kwargs['timestamp'], datetime)
                self.assertEqual(call_kwargs['timestamp'], expected)

    @patch('thunderbird_accounts.telemetry.client.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test', APP_ENV='test')
    def test_datetime_timestamp_passes_through(self, mock_posthog_class):
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        ts = datetime(2026, 4, 29, 2, 56, 51, tzinfo=timezone.utc)
        submit_event(distinct_id='abc', event='thundermail.x', timestamp=ts)

        self.assertIs(mock_client.capture.call_args.kwargs['timestamp'], ts)

    @patch('thunderbird_accounts.telemetry.client.Posthog')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test', APP_ENV='test')
    def test_none_timestamp_passes_through(self, mock_posthog_class):
        mock_client = MagicMock()
        mock_posthog_class.return_value = mock_client

        submit_event(distinct_id='abc', event='thundermail.x')

        self.assertIsNone(mock_client.capture.call_args.kwargs['timestamp'])
