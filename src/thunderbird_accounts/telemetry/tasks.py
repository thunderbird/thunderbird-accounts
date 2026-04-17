import logging
from datetime import datetime, timedelta, timezone

import sentry_sdk
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.telemetry.client import capture, hash_id, shutdown, _get_client

logger = logging.getLogger(__name__)

STALWART_CACHE_PREFIX = 'stalwart_uid:'
STALWART_CACHE_TTL = 3600

STALWART_FORWARDED_FIELDS = {'size'}


def _resolve_user_id(account_id=None, email=None):
    """Resolve a Stalwart accountId or email to a hashed Keycloak UUID.

    Tries accountId first (stable across email changes), then falls back
    to email lookup. Results are cached in Redis.
    """
    from thunderbird_accounts.mail.models import Account, Email

    cache_key = f'{STALWART_CACHE_PREFIX}{account_id or email}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached if cached != '' else None

    account = None

    if account_id is not None:
        try:
            account = Account.objects.select_related('user').get(stalwart_id=str(account_id))
        except Account.DoesNotExist:
            pass

    if account is None and email:
        try:
            account = Account.objects.select_related('user').get(name=email)
        except Account.DoesNotExist:
            try:
                email_obj = Email.objects.select_related('account__user').get(address=email)
                account = email_obj.account
            except Email.DoesNotExist:
                pass

    oidc_id = None
    if account and account.user and account.user.oidc_id:
        oidc_id = hash_id(account.user.oidc_id)

    cache.set(cache_key, oidc_id or '', STALWART_CACHE_TTL)
    return oidc_id


def _process_stalwart_event(event, client):
    """Process a single Stalwart webhook event: enrich and capture to PostHog."""
    event_type = event.get('type', '')
    posthog_event = settings.STALWART_EVENT_MAP.get(event_type)
    if not posthog_event:
        return False

    data = event.get('data', {})
    account_id = data.get('accountId')
    from_email = data.get('from')
    to_emails = data.get('to', [])

    if event_type.startswith('queue.queue-message'):
        identity_email = from_email
    else:
        identity_email = to_emails[0] if isinstance(to_emails, list) and to_emails else from_email

    distinct_id = _resolve_user_id(account_id=account_id, email=identity_email)
    if not distinct_id:
        logger.debug(f'Could not resolve user for event {event_type} (accountId={account_id}, email={identity_email})')
        return False

    properties = {key: data[key] for key in STALWART_FORWARDED_FIELDS if key in data}
    properties['stalwart_event_id'] = event.get('id', '')
    properties['environment'] = settings.APP_ENV
    properties['service'] = 'thundermail'

    client.capture(distinct_id=distinct_id, event=posthog_event, properties=properties)
    return True


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=300, max_retries=3)
def process_stalwart_events(self, events):
    """Process a batch of Stalwart webhook events: resolve users and forward to PostHog."""
    client = _get_client()
    if client is None:
        logger.debug('PostHog not configured, skipping Stalwart events')
        return {'task_status': 'skipped', 'reason': 'PostHog not configured'}

    submitted = 0
    skipped = 0

    try:
        for event in events:
            if _process_stalwart_event(event, client):
                submitted += 1
            else:
                skipped += 1

        if submitted:
            client.flush()
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.error(f'Failed to process Stalwart events: {exc}')
        raise self.retry(exc=exc)

    if submitted:
        logger.info(f'Stalwart events: submitted={submitted} skipped={skipped}')

    return {'task_status': 'success', 'events_submitted': submitted, 'events_skipped': skipped}


def _fetch_keycloak_events(client, date_from):
    """Fetch all events from Keycloak, paginating in configured page-size chunks.

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
                'max': settings.KEYCLOAK_EVENTS_PAGE_SIZE,
            },
        )
        page = response.json()
        all_events.extend(page)
        if len(page) < settings.KEYCLOAK_EVENTS_PAGE_SIZE:
            break
        offset += settings.KEYCLOAK_EVENTS_PAGE_SIZE
    return all_events


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=300, max_retries=3)
def poll_keycloak_events(self):
    """Poll the Keycloak Admin API for recent user events and submit them to PostHog.

    Keycloak's eventsExpiration is set short (30 min) to keep the events table small.
    This task runs every 15 minutes, deduplicating via a cached set of seen event IDs.
    Each event is hashed, stripped of PII, and submitted directly to PostHog.
    """
    if not settings.POSTHOG_API_KEY:
        logger.debug('POSTHOG_API_KEY not configured, skipping Keycloak event polling')
        return {'task_status': 'skipped', 'reason': 'POSTHOG_API_KEY not configured'}

    now = datetime.now(timezone.utc)
    today = now.strftime('%Y-%m-%d')

    cutoff_ms = int((now - timedelta(seconds=settings.KEYCLOAK_EVENT_POLL_INTERVAL_SECONDS + 30)).timestamp() * 1000)

    seen_event_ids = set(cache.get(settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY, []))

    try:
        client = KeycloakClient()

        # dateFrom=today is intentionally coarse; Keycloak's eventsExpiration (30 min)
        # limits the number of events available, so the response is always small.
        raw_events = _fetch_keycloak_events(client, today)
        event_map = settings.KEYCLOAK_EVENT_MAP
        all_events = [e for e in raw_events if e.get('time', 0) >= cutoff_ms and e.get('type') in event_map]

    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.error(f'Failed to fetch Keycloak events: {exc}')
        raise self.retry(exc=exc)

    if not all_events:
        logger.info('No Keycloak events found in polling window')
        return {'task_status': 'success', 'events_submitted': 0, 'events_skipped': 0}

    try:
        submitted = 0
        skipped = 0
        for event in all_events:
            event_id = event.get('id', '')
            if event_id in seen_event_ids:
                skipped += 1
                continue

            kc_type = event['type']
            user_id = event.get('userId')
            event_name = event_map[kc_type]

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

        # Cache every event ID from this poll so the next run can skip them.
        # Only IDs from the current poll are stored (not unioned with previous
        # runs) because Keycloak's eventsExpiration (30 min) guarantees older
        # events won't reappear.
        shutdown()
        all_seen_ids = [e['id'] for e in all_events if e.get('id')]
        cache.set(settings.KEYCLOAK_SEEN_EVENTS_CACHE_KEY, all_seen_ids, settings.KEYCLOAK_SEEN_EVENTS_CACHE_TTL)
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.error(f'Failed to submit events to PostHog: {exc}')
        raise self.retry(exc=exc)

    if skipped:
        logger.info(f'Skipped {skipped} events (no userId or already seen)')
    logger.info(f'Submitted {submitted} Keycloak events to PostHog')
    return {'task_status': 'success', 'events_submitted': submitted, 'events_skipped': skipped}
