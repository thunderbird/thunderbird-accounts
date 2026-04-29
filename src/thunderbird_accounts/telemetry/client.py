import hashlib
import logging
from datetime import datetime
from functools import cache

from django.conf import settings
from posthog import Posthog

logger = logging.getLogger(__name__)


@cache
def _make_client() -> Posthog:
    """Create and return a PostHog client (result is cached)."""
    return Posthog(settings.POSTHOG_API_KEY, host=settings.POSTHOG_HOST)


def _get_client() -> Posthog | None:
    """Return a cached PostHog client, or None if not configured."""
    if not settings.POSTHOG_API_KEY:
        return None
    return _make_client()


def hash_id(raw_id: str) -> str:
    """SHA-256 hash an identifier for use as a PostHog distinct_id."""
    return hashlib.sha256(raw_id.encode('utf-8')).hexdigest()


def submit_event(
    distinct_id: str,
    event: str,
    properties: dict | None = None,
    service: str = 'accounts',
    uuid: str | None = None,
    timestamp: str | datetime | None = None,
):
    """Submit an event to PostHog with an already-hashed distinct_id.

    service/environment are added automatically. Pass `uuid` and `timestamp`
    (RFC3339 string or datetime) when you have a stable source-side identifier
    and time; PostHog dedupes on (timestamp, distinct_id, event, uuid), so this
    makes retries idempotent. Callers that have a raw Keycloak user id should
    use capture() instead so hashing is centralized.
    """
    client = _get_client()
    if client is None:
        logger.debug(f'PostHog not configured, skipping event {event}')
        return

    # PostHog SDK silently drops events when timestamp is a string (its
    # guess_timezone() helper assumes a datetime), so parse RFC3339 here.
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    event_properties = {
        'environment': settings.APP_ENV,
        'service': service,
        **(properties or {}),
    }
    client.capture(
        distinct_id=distinct_id,
        event=event,
        properties=event_properties,
        uuid=uuid,
        timestamp=timestamp,
    )


def capture(event: str, keycloak_user_id: str, properties: dict | None = None, service: str = 'accounts'):
    """Submit an event to PostHog with standardized identity and privacy controls.

    All events are tagged with sha256(keycloak_user_id) as distinct_id,
    and service/environment are added automatically.
    """
    if not keycloak_user_id:
        logger.warning(f'No keycloak_user_id provided, skipping event {event}')
        return
    submit_event(
        distinct_id=hash_id(keycloak_user_id),
        event=event,
        properties=properties,
        service=service,
    )


def shutdown():
    """Flush pending events and tear down the client."""
    client = _get_client()
    if client is not None:
        client.shutdown()
    _make_client.cache_clear()
