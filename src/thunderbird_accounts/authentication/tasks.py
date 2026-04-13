import logging
from datetime import datetime, timedelta, timezone

import sentry_sdk
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.telemetry import capture, flush

logger = logging.getLogger(__name__)

EVENT_MAP = {
    'LOGIN': 'accounts.login',
    'LOGIN_ERROR': 'accounts.login_error',
    'REGISTER': 'accounts.register',
    'REGISTER_ERROR': 'accounts.register_error',
    'LOGOUT': 'accounts.logout',
    'CODE_TO_TOKEN': 'accounts.activity',
    'CODE_TO_TOKEN_ERROR': 'accounts.activity',
    'INTROSPECT_TOKEN': 'accounts.activity',
    'REFRESH_TOKEN': 'accounts.activity',
}

SEEN_EVENTS_CACHE_KEY = 'keycloak_poll:seen_event_ids'
SEEN_EVENTS_CACHE_TTL = 3600
EVENTS_PAGE_SIZE = 500


def _fetch_keycloak_events(client, date_from):
    """Fetch all events from Keycloak, paginating in EVENTS_PAGE_SIZE chunks.

    Which event types Keycloak records is controlled by enabledEventTypes in the
    realm config; callers are responsible for filtering to relevant types.
    """
    all_events = []
    offset = 0
    while True:
        response = client.request(
            'events',
            params={
                'dateFrom': date_from,
                'first': offset,
                'max': EVENTS_PAGE_SIZE,
            },
        )
        page = response.json()
        all_events.extend(page)
        if len(page) < EVENTS_PAGE_SIZE:
            break
        offset += EVENTS_PAGE_SIZE
    return all_events


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=300, max_retries=3)
def poll_keycloak_events(self):
    """Poll the Keycloak Admin API for recent user events and submit them to PostHog.

    Keycloak's eventsExpiration is set short (30 min) to keep the events table small.
    This task runs every 15 minutes, deduplicating via a cached set of seen event IDs.
    Each event is hashed, stripped of PII, and submitted directly to PostHog.
    """
    posthog_api_key = getattr(settings, 'POSTHOG_API_KEY', '')
    if not posthog_api_key:
        logger.debug('POSTHOG_API_KEY not configured, skipping Keycloak event polling')
        return {'task_status': 'skipped', 'reason': 'POSTHOG_API_KEY not configured'}

    now = datetime.now(timezone.utc)
    today = now.strftime('%Y-%m-%d')

    poll_interval = int(getattr(settings, 'KEYCLOAK_EVENT_POLL_INTERVAL_SECONDS', 900))
    cutoff_ms = int((now - timedelta(seconds=poll_interval + 30)).timestamp() * 1000)

    seen_event_ids = set(cache.get(SEEN_EVENTS_CACHE_KEY, []))

    try:
        client = KeycloakClient()

        # dateFrom=today is intentionally coarse; Keycloak's eventsExpiration (30 min)
        # limits the number of events available, so the response is always small.
        # EVENT_MAP filters which event types are forwarded to PostHog.
        raw_events = _fetch_keycloak_events(client, today)
        all_events = [e for e in raw_events if e.get('time', 0) >= cutoff_ms and e.get('type') in EVENT_MAP]

    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.error(f'Failed to fetch Keycloak events: {exc}')
        raise self.retry(exc=exc)

    if not all_events:
        logger.info('No Keycloak events found in polling window')
        return {'task_status': 'success', 'events_submitted': 0}

    try:
        submitted = 0
        skipped = 0
        new_seen_ids = set()
        for event in all_events:
            event_id = event.get('id', '')
            if event_id in seen_event_ids:
                skipped += 1
                continue

            kc_type = event.get('type', 'UNKNOWN')
            user_id = event.get('userId', '')
            event_name = EVENT_MAP.get(kc_type, 'accounts.activity')

            if not user_id:
                skipped += 1
                continue

            capture(
                event=event_name,
                keycloak_user_id=user_id,
                properties={
                    'clientId': event.get('clientId', ''),
                    'keycloak_event_type': kc_type,
                    'keycloak_event_id': event_id,
                    'is_error': kc_type.endswith('_ERROR'),
                },
            )
            submitted += 1
            if event_id:
                new_seen_ids.add(event_id)

        flush()
        # Cache every event ID from this poll so the next run can skip them.
        # Only IDs from the current poll are stored (not unioned with previous
        # runs) because Keycloak's eventsExpiration (30 min) guarantees older
        # events won't reappear. The TTL (1 hour) is deliberately longer than
        # the retention period so the cache survives delayed polls.
        all_seen_ids = [e.get('id', '') for e in all_events if e.get('id')]
        cache.set(SEEN_EVENTS_CACHE_KEY, all_seen_ids, SEEN_EVENTS_CACHE_TTL)
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.error(f'Failed to submit events to PostHog: {exc}')
        raise self.retry(exc=exc)

    if skipped:
        logger.info(f'Skipped {skipped} events (no userId or already seen)')
    logger.info(f'Submitted {submitted} Keycloak events to PostHog')
    return {'task_status': 'success', 'events_submitted': submitted, 'events_skipped': skipped}
