import datetime

import requests.exceptions
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.mail.clients import MailClient


def health_check(request: HttpRequest):
    """Do nothing, only prove the service is responsive."""

    # Retrieve the list of required actions as a no-op action to demonstrate that keycloak's api is reachable and
    # operational.
    try:
        keycloak_client = KeycloakClient()
        keycloak_client.request('authentication/required-actions')
    except requests.exceptions.HTTPError:
        return HttpResponse('Keycloak cannot be reached', status=500)

    # Retrieve telemetry results as a no-op action to demonstrate that stalwart's api is reachable and operational.
    try:
        stalwart_client = MailClient()
        stalwart_client.get_telemetry()
    except requests.exceptions.HTTPError:
        return HttpResponse('Stalwart cannot be reached', status=500)

    # Set and retrieve the current timestamp to demonstrate that redis is reachable and operational.
    try:
        now = datetime.datetime.now(datetime.UTC)
        cache.set('__tbaccounts_health', now)
        cache_now = cache.get('__tbaccounts_health')
        if now != cache_now:
            return HttpResponse('Redis not returning correct results')
    except Exception:
        return HttpResponse('Redis cannot be reached', status=500)

    return HttpResponse('Aliveness demonstrated!')
