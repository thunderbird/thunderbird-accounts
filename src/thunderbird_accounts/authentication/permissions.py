import logging
from urllib.parse import urlparse

import sentry_sdk

from rest_framework.permissions import BasePermission
from rest_framework.authentication import BaseAuthentication

from thunderbird_accounts import settings
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.client.models import ClientEnvironment

# We don't want hard requirements on having paddle package installed
try:
    from paddle_billing.Notifications import Verifier, Secret
except ImportError:
    Verifier, Secret = None, None


class IsClient(BasePermission):
    """
    Allows access only to Clients matching secret, host, and activeness.
    """

    def has_permission(self, request, view):
        host = (
            request.headers.get('origin') or f'{request.scheme}://{request.get_host()}'
        )  # We're not forwarding hosts correctly, cors middleware uses origin so we should too.
        client_secret = request.data.get('secret')
        if not client_secret:
            logging.debug('[IsClient] failed: No client secret')
            return False

        try:
            client_env: ClientEnvironment = ClientEnvironment.objects.get(auth_token=client_secret)
        except ClientEnvironment.DoesNotExist:
            logging.debug('[IsClient] failed: Provided secret is not associated with a client environment')
            return False

        allowed_hostnames = client_env.allowed_hostnames

        parsed_url = urlparse(host) or host
        is_host_valid = any([allowed_hostname == parsed_url.netloc for allowed_hostname in allowed_hostnames])

        # Check if the client env is not active, or if the host is valid
        if not client_env.is_active or not is_host_valid:
            err = f'[IsClient] failed: Client environment is not active or host is invalid: {host}'
            logging.debug(err)
            sentry_sdk.capture_message(err)
            return False

        # Append client_env to request
        request.client_env = client_env

        return True


class IsValidPaddleWebhook(BaseAuthentication):
    def authenticate(self, request):
        if not Verifier or not Secret:
            logging.error('Paddle package is not installed. This webhook has been rejected.')
            return None

        integrity_check = Verifier().verify(request, Secret(settings.PADDLE_WEBHOOK_KEY))

        if not integrity_check:
            return None

        # We need to return a user, but we don't need the user for these requests
        # So return an empty user object
        return User(), None
