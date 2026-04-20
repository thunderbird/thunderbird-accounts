from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from thunderbird_accounts.telemetry.tasks import poll_keycloak_events

import thunderbird_accounts.telemetry.client as telemetry_module

_EVENT_COUNTER = 0


def _make_keycloak_event(
    event_type,
    user_id='fake-user-uuid',
    client_id='tb-accounts',
    event_id=None,
    details=None,
    include_client_id=True,
):
    global _EVENT_COUNTER
    if event_id is None:
        _EVENT_COUNTER += 1
        event_id = f'evt-{_EVENT_COUNTER}'
    event = {
        'type': event_type,
        'userId': user_id,
        'id': event_id,
        'time': 9999999999999,
    }
    if include_client_id:
        event['clientId'] = client_id
    if details is not None:
        event['details'] = details
    return event


@override_settings(POSTHOG_API_KEY='phc_test', POSTHOG_HOST='https://ph.test')
class PollKeycloakEventsTestCase(TestCase):
    def setUp(self):
        telemetry_module._make_client.cache_clear()
        cache.delete(settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY)
        self.addCleanup(telemetry_module._make_client.cache_clear)
        self.addCleanup(cache.delete, settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY)

        posthog_patcher = patch('thunderbird_accounts.telemetry.client.Posthog')
        kc_patcher = patch('thunderbird_accounts.telemetry.tasks.KeycloakClient')
        self.mock_posthog_class = posthog_patcher.start()
        self.mock_kc_class = kc_patcher.start()
        self.addCleanup(posthog_patcher.stop)
        self.addCleanup(kc_patcher.stop)

        self.mock_ph = MagicMock()
        self.mock_posthog_class.return_value = self.mock_ph

    def _set_keycloak_events(self, events):
        """Configure the KeycloakClient mock to return paginated slices of the event list."""
        mock_kc_client = MagicMock()
        self.mock_kc_class.return_value = mock_kc_client

        def fake_request(endpoint, params=None):
            first = (params or {}).get('first', 0)
            max_results = (params or {}).get('max', settings.KEYCLOAK_EVENTS_PAGE_SIZE)
            page = events[first:first + max_results]
            resp = MagicMock()
            resp.json.return_value = page
            return resp

        mock_kc_client.request.side_effect = fake_request
        return mock_kc_client

    def _last_capture_properties(self):
        return self.mock_ph.capture.call_args.kwargs['properties']

    @override_settings(POSTHOG_API_KEY=None)
    def test_skips_when_posthog_not_configured(self):
        result = poll_keycloak_events()
        self.assertEqual(result['task_status'], 'skipped')

    def test_no_events_returns_zero(self):
        self._set_keycloak_events([])

        result = poll_keycloak_events()
        self.assertEqual(result['task_status'], 'success')
        self.assertEqual(result['events_submitted'], 0)

    def test_raw_user_id_never_in_posthog_payload(self):
        """The raw Keycloak UUID must not appear anywhere in the PostHog call."""
        secret_uuid = 'secret-keycloak-uuid-12345'
        self._set_keycloak_events([_make_keycloak_event('LOGIN', user_id=secret_uuid)])

        poll_keycloak_events()

        call_kwargs = self.mock_ph.capture.call_args.kwargs
        self.assertNotEqual(call_kwargs['distinct_id'], secret_uuid)
        for value in call_kwargs['properties'].values():
            if isinstance(value, str):
                self.assertNotEqual(value, secret_uuid)

    def test_unmapped_event_types_are_filtered_out(self):
        """Events with types not in KEYCLOAK_EVENT_MAP must not be forwarded."""
        self._set_keycloak_events([_make_keycloak_event('CLIENT_LOGIN')])

        result = poll_keycloak_events()
        self.mock_ph.capture.assert_not_called()
        self.assertEqual(result['events_submitted'], 0)

    def test_duplicate_events_are_skipped(self):
        """Events already in the seen-ID cache must not be resubmitted."""
        self._set_keycloak_events([_make_keycloak_event('LOGIN', event_id='already-seen')])
        cache.set(settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY, ['already-seen'])

        result = poll_keycloak_events()
        self.mock_ph.capture.assert_not_called()
        self.assertEqual(result['events_submitted'], 0)
        self.assertEqual(result['events_skipped'], 1)

    def test_seen_ids_are_persisted_to_cache(self):
        """After a successful run, submitted event IDs should be in the cache."""
        self._set_keycloak_events([_make_keycloak_event('LOGIN', event_id='new-event-123')])

        poll_keycloak_events()

        cached = cache.get(settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY)
        self.assertIn('new-event-123', cached)

    def test_is_error_flag_for_all_event_types(self):
        """Every mapped event type is submitted with the correct is_error flag."""
        # Hardcoded so the test catches regressions in the _ERROR suffix rule
        # (instead of re-deriving it the same way the production code does).
        expected_is_error = {
            'LOGIN': False,
            'LOGIN_ERROR': True,
            'REGISTER': False,
            'REGISTER_ERROR': True,
            'LOGOUT': False,
            'CODE_TO_TOKEN': False,
            'CODE_TO_TOKEN_ERROR': True,
            'INTROSPECT_TOKEN': False,
            'REFRESH_TOKEN': False,
        }
        # If a new type is added to KEYCLOAK_EVENT_MAP, extend the table above.
        self.assertEqual(set(expected_is_error), set(settings.KEYCLOAK_EVENT_MAP))

        self._set_keycloak_events([_make_keycloak_event(kc_type) for kc_type in expected_is_error])

        poll_keycloak_events()

        submitted = {
            call.kwargs['properties']['keycloak_event_type']: call.kwargs['properties']['is_error']
            for call in self.mock_ph.capture.call_args_list
        }
        self.assertEqual(submitted, expected_is_error)

    @override_settings(KEYCLOAK_EVENTS_PAGE_SIZE=3)
    def test_pagination_fetches_all_events(self):
        """Events spanning multiple pages must all be fetched and submitted."""
        mock_kc_client = self._set_keycloak_events([_make_keycloak_event('LOGIN') for _ in range(7)])

        poll_keycloak_events()
        self.assertEqual(self.mock_ph.capture.call_count, 7)
        self.assertEqual(mock_kc_client.request.call_count, 3)  # pages: 3+3+1

    def test_client_id_resolution(self):
        """clientId is attributed (token_issued_for or top-level); keycloakCallerClientId is raw Keycloak clientId."""
        cases = [
            (
                'INTROSPECT_TOKEN from stalwart for a send-backend token: attributed=send-backend, caller=stalwart',
                _make_keycloak_event(
                    'INTROSPECT_TOKEN',
                    client_id='stalwart',
                    details={
                        'token_issued_for': 'thunderbird-send-backend',
                        'token_id': 'ofrtrt:fake',
                        'token_type': 'Bearer',
                        'client_auth_method': 'client-secret',
                    },
                ),
                'thunderbird-send-backend',
                'stalwart',
            ),
            (
                'INTROSPECT_TOKEN from send-backend directly: attributed and caller both send-backend',
                _make_keycloak_event(
                    'INTROSPECT_TOKEN',
                    client_id='thunderbird-send-backend',
                    details={
                        'token_issued_for': 'thunderbird-send-backend',
                        'token_id': 'ofrtrt:fake',
                        'token_type': 'Bearer',
                        'client_auth_method': 'client-secret',
                    },
                ),
                'thunderbird-send-backend',
                'thunderbird-send-backend',
            ),
            (
                'LOGIN has no details; top-level clientId wins for both fields',
                _make_keycloak_event('LOGIN', client_id='desktop'),
                'desktop',
                'desktop',
            ),
            (
                'no top-level clientId and no token_issued_for',
                _make_keycloak_event('LOGIN', include_client_id=False),
                None,
                None,
            ),
        ]

        for label, event, expected_client_id, expected_caller in cases:
            with self.subTest(case=label):
                self.mock_ph.reset_mock()
                cache.delete(settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY)
                self._set_keycloak_events([event])

                poll_keycloak_events()

                props = self._last_capture_properties()
                self.assertEqual(props['clientId'], expected_client_id)
                self.assertEqual(props['keycloakCallerClientId'], expected_caller)
