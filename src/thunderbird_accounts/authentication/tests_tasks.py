from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from thunderbird_accounts.authentication.tasks import (
    poll_keycloak_events,
    EVENT_MAP,
    EVENTS_PAGE_SIZE,
    SEEN_EVENTS_CACHE_KEY,
)

import thunderbird_accounts.telemetry as telemetry_module

_EVENT_COUNTER = 0


def _make_keycloak_event(event_type, user_id='fake-user-uuid', client_id='tb-accounts', event_id=None):
    global _EVENT_COUNTER
    if event_id is None:
        _EVENT_COUNTER += 1
        event_id = f'evt-{_EVENT_COUNTER}'
    return {
        'type': event_type,
        'userId': user_id,
        'clientId': client_id,
        'id': event_id,
        'time': 9999999999999,
    }


def _setup_keycloak_mock(mock_kc_class, events):
    """Configure the KeycloakClient mock to return paginated slices of the event list."""
    mock_kc_client = MagicMock()
    mock_kc_class.return_value = mock_kc_client

    def fake_request(endpoint, params=None):
        first = (params or {}).get('first', 0)
        max_results = (params or {}).get('max', EVENTS_PAGE_SIZE)
        page = events[first:first + max_results]
        resp = MagicMock()
        resp.json.return_value = page
        return resp

    mock_kc_client.request.side_effect = fake_request
    return mock_kc_client


class PollKeycloakEventsTestCase(TestCase):
    def setUp(self):
        telemetry_module._client = None
        cache.delete(SEEN_EVENTS_CACHE_KEY)

    def tearDown(self):
        telemetry_module._client = None
        cache.delete(SEEN_EVENTS_CACHE_KEY)

    @override_settings(POSTHOG_API_KEY='')
    def test_skips_when_posthog_not_configured(self):
        result = poll_keycloak_events()
        self.assertEqual(result['task_status'], 'skipped')

    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_no_events_returns_zero(self, mock_kc_class, mock_posthog_class):
        _setup_keycloak_mock(mock_kc_class, [])
        mock_posthog_class.return_value = MagicMock()

        result = poll_keycloak_events()
        self.assertEqual(result['task_status'], 'success')
        self.assertEqual(result['events_submitted'], 0)

    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_raw_user_id_never_in_posthog_payload(self, mock_kc_class, mock_posthog_class):
        """The raw Keycloak UUID must not appear anywhere in the PostHog call."""
        mock_ph = MagicMock()
        mock_posthog_class.return_value = mock_ph
        secret_uuid = 'secret-keycloak-uuid-12345'

        _setup_keycloak_mock(mock_kc_class, [_make_keycloak_event('LOGIN', user_id=secret_uuid)])

        poll_keycloak_events()

        call_kwargs = mock_ph.capture.call_args.kwargs
        self.assertNotEqual(call_kwargs['distinct_id'], secret_uuid)
        for value in call_kwargs['properties'].values():
            if isinstance(value, str):
                self.assertNotEqual(value, secret_uuid)

    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_unmapped_event_types_are_filtered_out(self, mock_kc_class, mock_posthog_class):
        """Events with types not in EVENT_MAP must not be forwarded."""
        mock_ph = MagicMock()
        mock_posthog_class.return_value = mock_ph

        _setup_keycloak_mock(mock_kc_class, [_make_keycloak_event('CLIENT_LOGIN')])

        result = poll_keycloak_events()
        mock_ph.capture.assert_not_called()
        self.assertEqual(result['events_submitted'], 0)

    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_duplicate_events_are_skipped(self, mock_kc_class, mock_posthog_class):
        """Events already in the seen-ID cache must not be resubmitted."""
        mock_ph = MagicMock()
        mock_posthog_class.return_value = mock_ph

        _setup_keycloak_mock(mock_kc_class, [_make_keycloak_event('LOGIN', event_id='already-seen')])

        cache.set(SEEN_EVENTS_CACHE_KEY, ['already-seen'])

        result = poll_keycloak_events()
        mock_ph.capture.assert_not_called()
        self.assertEqual(result['events_submitted'], 0)
        self.assertEqual(result['events_skipped'], 1)

    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_seen_ids_are_persisted_to_cache(self, mock_kc_class, mock_posthog_class):
        """After a successful run, submitted event IDs should be in the cache."""
        mock_ph = MagicMock()
        mock_posthog_class.return_value = mock_ph

        _setup_keycloak_mock(mock_kc_class, [_make_keycloak_event('LOGIN', event_id='new-event-123')])

        poll_keycloak_events()

        cached = cache.get(SEEN_EVENTS_CACHE_KEY)
        self.assertIn('new-event-123', cached)

    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_is_error_flag_for_all_event_types(self, mock_kc_class, mock_posthog_class):
        """Exercise every mapped event type through the task and verify is_error matches the _ERROR suffix."""
        mock_ph = MagicMock()
        mock_posthog_class.return_value = mock_ph

        all_events = [_make_keycloak_event(kc_type) for kc_type in EVENT_MAP]
        _setup_keycloak_mock(mock_kc_class, all_events)

        poll_keycloak_events()

        submitted_types = {}
        for call_obj in mock_ph.capture.call_args_list:
            props = call_obj.kwargs['properties']
            submitted_types[props['keycloak_event_type']] = props['is_error']

        for kc_type in EVENT_MAP:
            self.assertIn(kc_type, submitted_types, f'{kc_type} was not submitted')
            expected_error = kc_type.endswith('_ERROR')
            self.assertEqual(
                submitted_types[kc_type],
                expected_error,
                f'{kc_type}: expected is_error={expected_error}, got {submitted_types[kc_type]}',
            )

    @patch('thunderbird_accounts.authentication.tasks.EVENTS_PAGE_SIZE', 3)
    @patch('thunderbird_accounts.telemetry.Posthog')
    @patch('thunderbird_accounts.authentication.tasks.KeycloakClient')
    @override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
    def test_pagination_fetches_all_events(self, mock_kc_class, mock_posthog_class):
        """Events spanning multiple pages must all be fetched and submitted."""
        mock_ph = MagicMock()
        mock_posthog_class.return_value = mock_ph

        events = [_make_keycloak_event('LOGIN') for _ in range(7)]
        mock_kc_client = _setup_keycloak_mock(mock_kc_class, events)

        poll_keycloak_events()
        self.assertEqual(mock_ph.capture.call_count, 7)
        self.assertEqual(mock_kc_client.request.call_count, 3)  # pages: 3+3+1
