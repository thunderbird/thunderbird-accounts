"""Tests for Stalwart telemetry: webhook view, user resolver, event processor."""
import base64
import hashlib
import hmac
import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.telemetry.client import hash_id
from thunderbird_accounts.telemetry.tasks import _process_stalwart_event, _resolve_user_id


WEBHOOK_URL = '/api/v1/telemetry/stalwart/webhook/'


def _sign(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()).decode('ascii')


class StalwartWebhookViewTestCase(TestCase):
    """HMAC gate, dev bypass, method guard, and task enqueue wiring.

    Goes through self.client so URL resolution, csrf_exempt, and require_POST
    are all exercised alongside the view logic.
    """

    SECRET = 'test-webhook-secret'

    def setUp(self):
        self.body = json.dumps(
            {'events': [{'id': 'e1', 'createdAt': '2024-01-01T00:00:00Z', 'type': 'message-ingest.ham', 'data': {}}]}
        ).encode('utf-8')

    def _post(self, signature=None):
        extra = {'HTTP_X_SIGNATURE': signature} if signature else {}
        return self.client.post(WEBHOOK_URL, data=self.body, content_type='application/json', **extra)

    @patch('thunderbird_accounts.telemetry.tasks.process_stalwart_events')
    @override_settings(STALWART_WEBHOOK_SECRET=SECRET, IS_DEV=False)
    def test_valid_signature_enqueues_task(self, mock_task):
        response = self._post(signature=_sign(self.body, self.SECRET))

        self.assertEqual(response.status_code, 200)
        mock_task.delay.assert_called_once()

    @patch('thunderbird_accounts.telemetry.tasks.process_stalwart_events')
    @override_settings(STALWART_WEBHOOK_SECRET=SECRET, IS_DEV=False)
    def test_invalid_signature_rejects(self, mock_task):
        response = self._post(signature='not-the-right-signature')

        self.assertEqual(response.status_code, 403)
        mock_task.delay.assert_not_called()

    @patch('thunderbird_accounts.telemetry.tasks.process_stalwart_events')
    @override_settings(STALWART_WEBHOOK_SECRET=None, IS_DEV=False)
    def test_missing_secret_rejects_outside_dev(self, mock_task):
        response = self._post()

        self.assertEqual(response.status_code, 503)
        mock_task.delay.assert_not_called()

    @patch('thunderbird_accounts.telemetry.tasks.process_stalwart_events')
    @override_settings(STALWART_WEBHOOK_SECRET=None, IS_DEV=True)
    def test_dev_bypass_accepts_unsigned(self, mock_task):
        response = self._post()

        self.assertEqual(response.status_code, 200)
        mock_task.delay.assert_called_once()

    @patch('thunderbird_accounts.telemetry.tasks.process_stalwart_events')
    @override_settings(STALWART_WEBHOOK_SECRET=SECRET, IS_DEV=False)
    def test_get_is_rejected(self, mock_task):
        """require_POST should reject GET without touching signature checks or the task."""
        response = self.client.get(WEBHOOK_URL)

        self.assertEqual(response.status_code, 405)
        mock_task.delay.assert_not_called()


class ResolveUserIdTestCase(TestCase):
    """User resolution: the returned id is always hashed (never raw), across all lookup paths."""

    OIDC_ID = 'keycloak-user-uuid-abc'

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

        self.user = User.objects.create_user('alice', 'alice@thundermail.test', 'x')
        self.user.oidc_id = self.OIDC_ID
        self.user.save()

        self.account = Account.objects.create(
            name='alice@thundermail.test',
            user_id=self.user.uuid,
            stalwart_id='stalwart-acct-1',
        )

    def test_resolves_by_stalwart_id_returning_hashed_oidc(self):
        """Primary lookup path; also enforces the privacy invariant (raw oidc never returned)."""
        result = _resolve_user_id(account_id='stalwart-acct-1')

        self.assertEqual(result, hash_id(self.OIDC_ID))
        self.assertNotEqual(result, self.OIDC_ID)

    def test_resolves_by_primary_email(self):
        result = _resolve_user_id(email='alice@thundermail.test')
        self.assertEqual(result, hash_id(self.OIDC_ID))

    def test_resolves_by_alias_email_via_email_table(self):
        """Fallback path: email doesn't match any Account.name, but matches an Email alias row."""
        Email.objects.create(address='alias@thundermail.test', account=self.account, type=Email.EmailType.ALIAS)

        result = _resolve_user_id(email='alias@thundermail.test')
        self.assertEqual(result, hash_id(self.OIDC_ID))


class ProcessStalwartEventTestCase(TestCase):
    """Identity-email selection per event kind, and dedup field passthrough."""

    def setUp(self):
        self.submit_patcher = patch('thunderbird_accounts.telemetry.tasks.submit_event')
        self.resolve_patcher = patch(
            'thunderbird_accounts.telemetry.tasks._resolve_user_id', return_value='hashed-id'
        )
        self.mock_submit = self.submit_patcher.start()
        self.mock_resolve = self.resolve_patcher.start()
        self.addCleanup(self.submit_patcher.stop)
        self.addCleanup(self.resolve_patcher.stop)

    def test_ingest_event_uses_first_recipient_as_identity(self):
        """message-ingest events identify the inbox owner via the `to` list."""
        _process_stalwart_event({
            'id': 'e1',
            'createdAt': '2024-01-01T00:00:00Z',
            'type': 'message-ingest.ham',
            'data': {'from': 'sender@elsewhere.test', 'to': ['owner@thundermail.test'], 'accountId': 42},
        })

        self.mock_resolve.assert_called_once_with(account_id=42, email='owner@thundermail.test')

    def test_queue_event_uses_sender_as_identity(self):
        """queue.queue-message-* events identify the sender, since the inbox owner is the `from`."""
        _process_stalwart_event({
            'id': 'e2',
            'createdAt': '2024-01-01T00:00:00Z',
            'type': 'queue.queue-message-authenticated',
            'data': {'from': 'owner@thundermail.test', 'to': ['recipient@elsewhere.test']},
        })

        self.mock_resolve.assert_called_once_with(account_id=None, email='owner@thundermail.test')

    def test_forwards_stalwart_id_and_created_at_for_posthog_dedup(self):
        """uuid + timestamp must flow through unchanged so PostHog can dedupe on Celery retries."""
        _process_stalwart_event({
            'id': 'stalwart-evt-abc',
            'createdAt': '2024-01-01T12:34:56Z',
            'type': 'message-ingest.ham',
            'data': {'to': ['owner@thundermail.test']},
        })

        kwargs = self.mock_submit.call_args.kwargs
        self.assertEqual(kwargs['uuid'], 'stalwart-evt-abc')
        self.assertEqual(kwargs['timestamp'], '2024-01-01T12:34:56Z')
