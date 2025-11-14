import logging
import time
import requests.exceptions

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient

from datetime import datetime
from uuid import uuid4 as UUID


class PerformanceMonitored:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        start = time.perf_counter()
        result = self.func(*args, **kwargs)
        finish = time.perf_counter()
        duration = finish - start
        logging.debug(f'Performance monitoring -- Function {self.func} ran in {duration} seconds')
        return result, duration


def health_check(request: HttpRequest):
    """Prove the service is responsive."""

    @PerformanceMonitored
    def __check_keycloak():
        # Retrieve the list of required actions as a no-op action to demonstrate that keycloak's api is reachable and
        # operational.
        try:
            keycloak_client = KeycloakClient()
            keycloak_client.request('authentication/required-actions')
            return True
        except requests.exceptions.HTTPError:
            return False

    @PerformanceMonitored
    def __check_stalwart():
        # Retrieve telemetry results as a no-op action to demonstrate that stalwart's api is reachable and operational.
        try:
            stalwart_client = MailClient()
            stalwart_client.get_telemetry()
            return True
        except requests.exceptions.HTTPError:
            return False

    @PerformanceMonitored
    def __check_redis():
        # Set and retrieve the current timestamp to demonstrate that redis is reachable and operational.
        try:
            key = f'health_check_{UUID()}'
            now = datetime.now().isoformat()
            cache.set(key, now)
            then = cache.get(key)
            cache.delete(key)
            return True if now == then else False
        except Exception:
            return False

    @PerformanceMonitored
    def __check_postgres():
        try:
            User.objects.first()
            return True
        except Exception:
            return False

    keycloak_health, keycloak_duration = __check_keycloak()
    stalwart_health, stalwart_duration = __check_stalwart()
    redis_health, redis_duration = __check_redis()
    postgres_health, postgres_duration = __check_postgres()
    total_duration = keycloak_duration + stalwart_duration + redis_duration + postgres_duration
    accounts_health = all([keycloak_health, stalwart_health, redis_health, postgres_health])

    connection_stats = {
        'keycloak': {'healthy': keycloak_health, 'duration': keycloak_duration},
        'stalwart': {'healthy': stalwart_health, 'duration': stalwart_duration},
        'redis': {'healthy': redis_health, 'duration': redis_duration},
        'database': {'healthy': postgres_health, 'duration': postgres_duration},
        'accounts': {'healthy': accounts_health, 'duration': total_duration},
    }

    return JsonResponse(connection_stats)
