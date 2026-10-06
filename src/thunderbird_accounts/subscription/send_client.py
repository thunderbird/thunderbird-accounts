from urllib.parse import quote

import requests
from django.conf import settings


class SendClientError(Exception):
    pass


class SendUserNotFound(SendClientError):
    pass


def is_send_api_configured() -> bool:
    return bool(settings.TB_PRO_SEND_API_URL and settings.TB_PRO_SEND_API_KEY)


def get_send_storage_usage(oidc_id: str) -> dict:
    """Retrieve a user's Send storage usage from Send's internal service-to-service API.

    Returns a dict with ``active`` (used bytes) and ``limit`` (quota bytes).
    """
    if not is_send_api_configured():
        raise SendClientError('Send API is not configured')

    base_url = settings.TB_PRO_SEND_API_URL.rstrip('/')
    url = f'{base_url}/api/internal/users/{quote(oidc_id, safe="")}/storage'

    try:
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {settings.TB_PRO_SEND_API_KEY}',
                'Accept': 'application/json',
            },
            timeout=settings.TB_PRO_SEND_API_TIMEOUT,
        )
    except requests.RequestException as ex:
        raise SendClientError(f'Error contacting Send: {ex}') from ex

    if response.status_code == 404:
        raise SendUserNotFound('User not found on Send')

    if not response.ok:
        raise SendClientError(f'Send responded with status {response.status_code}')

    try:
        data = response.json()
        return {'active': int(data['active']), 'limit': int(data['limit'])}
    except (ValueError, KeyError, TypeError) as ex:
        raise SendClientError(f'Unexpected response from Send: {ex}') from ex
