import hashlib
import logging
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


def capture(event: str, keycloak_user_id: str, properties: dict | None = None):
    """Submit an event to PostHog with standardized identity and privacy controls.

    All events are tagged with sha256(keycloak_user_id) as distinct_id,
    and service/environment are added automatically.
    """
    client = _get_client()
    if client is None:
        logger.debug(f'PostHog not configured, skipping event {event}')
        return

    if not keycloak_user_id:
        logger.warning(f'No keycloak_user_id provided, skipping event {event}')
        return

    distinct_id = hash_id(keycloak_user_id)
    env = settings.APP_ENV

    event_properties = {
        'environment': env,
        'service': 'accounts',
        **(properties or {}),
    }

    client.capture(distinct_id=distinct_id, event=event, properties=event_properties)


def shutdown():
    """Flush pending events and tear down the client."""
    client = _get_client()
    if client is not None:
        client.shutdown()
    _make_client.cache_clear()
