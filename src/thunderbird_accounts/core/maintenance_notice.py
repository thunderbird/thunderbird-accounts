"""The login page's maintenance notice, read from the tbpro realm overrides so Accounts pages show it too.

The override keys are documented in docs/keycloak/maintenance-notice.rst. Validation mirrors the login
theme (keycloak/themes/tbpro/assets/vue/views/LoginView/index.vue)."""

import logging
from typing import Optional, TypedDict

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from requests.exceptions import RequestException

from thunderbird_accounts.authentication.clients import KeycloakClient

logger = logging.getLogger(__name__)

# Accounts is English-only, so it reads the English realm overrides.
OVERRIDES_ENDPOINT = 'localization/en'
NOTICE_TYPES = ('info', 'warning', 'critical')
DEFAULT_NOTICE_TYPE = 'warning'

validate_status_url = URLValidator(schemes=['http', 'https'])


class MaintenanceNotice(TypedDict):
    text: str
    type: str
    statusUrl: Optional[str]
    statusText: Optional[str]


def get_maintenance_notice() -> Optional[MaintenanceNotice]:
    """Returns the notice to show, or None when none is set or the overrides can't be read."""
    # Only defined when AUTH_SCHEME is oidc.
    if not getattr(settings, 'KEYCLOAK_API_ENDPOINT', None):
        return None

    notice = cache.get(settings.MAINTENANCE_NOTICE_CACHE_KEY)
    if notice is None:
        # A miss reads as None, so "no notice" is cached as an empty dict.
        notice = read_maintenance_notice() or {}
        cache.set(settings.MAINTENANCE_NOTICE_CACHE_KEY, notice, settings.MAINTENANCE_NOTICE_CACHE_SECONDS)
    return notice or None


def read_maintenance_notice() -> Optional[MaintenanceNotice]:
    try:
        response = KeycloakClient().request(OVERRIDES_ENDPOINT, timeout=settings.MAINTENANCE_NOTICE_TIMEOUT_SECONDS)
        overrides = response.json()
    except (RequestException, ValueError, KeyError) as ex:
        logger.warning(f'[maintenance_notice] Could not read the realm overrides: {ex!r}')
        return None

    if not isinstance(overrides, dict):
        logger.warning('[maintenance_notice] The realm overrides response is not an object')
        return None

    text = _stripped(overrides.get('maintenanceNotice'))
    if not text:
        return None

    notice_type = overrides.get('maintenanceNoticeType')
    status_url = _stripped(overrides.get('maintenanceNoticeStatusUrl'))
    try:
        validate_status_url(status_url)
    except ValidationError:
        status_url = None

    return {
        'text': text,
        'type': notice_type if notice_type in NOTICE_TYPES else DEFAULT_NOTICE_TYPE,
        'statusUrl': status_url,
        'statusText': _stripped(overrides.get('maintenanceNoticeStatusText')) or None,
    }


def _stripped(value) -> str:
    return value.strip() if isinstance(value, str) else ''
