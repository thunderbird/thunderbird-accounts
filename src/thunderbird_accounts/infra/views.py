import requests.exceptions
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient


def health_check(request: HttpRequest):
    """Prove the service is responsive."""

    connection_stats = {
        'keycloak': True,
        'stalwart': True,
        'redis': True,
        'database': True,
        'accounts': True,
    }

    # Retrieve the list of required actions as a no-op action to demonstrate that keycloak's api is reachable and
    # operational.
    try:
        keycloak_client = KeycloakClient()
        keycloak_client.request('authentication/required-actions')
    except requests.exceptions.HTTPError:
        connection_stats['keycloak'] = False

    # Retrieve telemetry results as a no-op action to demonstrate that stalwart's api is reachable and operational.
    try:
        stalwart_client = MailClient()
        stalwart_client.get_telemetry()
    except requests.exceptions.HTTPError:
        connection_stats['stalwart'] = False

    # Set and retrieve the current timestamp to demonstrate that redis is reachable and operational.
    try:
        cache.get('__tbaccounts_health')
    except Exception:
        connection_stats['redis'] = False

    try:
        User.objects.first()
    except Exception:
        connection_stats['database'] = False

    return JsonResponse(connection_stats)
