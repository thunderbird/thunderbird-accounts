import hashlib
import logging
import os

from django.conf import settings
from posthog import Posthog

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> Posthog | None:
    """Return a singleton PostHog client, or None if not configured."""
    global _client  # noqa: PLW0603
    if _client is not None:
        return _client

    api_key = getattr(settings, 'POSTHOG_API_KEY', '')
    host = getattr(settings, 'POSTHOG_HOST', 'https://us.i.posthog.com')

    if not api_key:
        return None

    _client = Posthog(api_key, host=host)
    return _client


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
        logger.debug('PostHog not configured, skipping event %s', event)
        return

    if not keycloak_user_id:
        logger.warning('No keycloak_user_id provided, skipping event %s', event)
        return

    distinct_id = hash_id(keycloak_user_id)
    env = os.getenv('APP_ENV', 'dev')

    event_properties = {
        'environment': env,
        'service': 'accounts',
        **(properties or {}),
    }

    client.capture(distinct_id=distinct_id, event=event, properties=event_properties)


def flush():
    """Flush any pending events and reset the client."""
    global _client  # noqa: PLW0603
    if _client is not None:
        _client.flush()
        _client = None
