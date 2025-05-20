import datetime
import logging
from urllib.parse import urlparse

import jwt
import sentry_sdk

from rest_framework.permissions import BasePermission
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from fxa.oauth import Client

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


class IsValidFXAWebhook(BaseAuthentication):
    def authenticate(self, request):
        """A port of get_webhook_auth from Appointment. We don't have a great way to test this flow since setting up
        FXA locally is a bit of work. But we know this auth flow does work from our time using it on Appointment.

        Take in the SET from the fxa event broker and verify its authenticity with various methods
        according to FXA docs. (See: https://github.com/mozilla/fxa/blob/main/packages/fxa-event-broker/README.md)

        Once we've confirmed it's all good, we can grab the User associated with the fxa id (sub) and return that
        and the decoded jwt (which contains event info.)
        """
        auth_header = request.headers.get('authorization')
        if not auth_header:
            logging.error('FXA webhook event with no authorization.')
            raise AuthenticationFailed('Authorization header is required')

        header_type, header_token = auth_header.split(' ')
        if header_type != 'Bearer':
            logging.error(f'Error decoding token. Type == {header_type}, which is not Bearer!')
            raise AuthenticationFailed('A bearer token is required')

        client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
        open_id_config = client.apiclient.get(settings.FXA_OPEN_ID_CONFIG_URL)
        public_jwks = client.apiclient.get('/jwks').get('keys', [])

        if not public_jwks:
            logging.error('No public jwks available.')
            raise AuthenticationFailed('Could not retrieve jwks for token verification')

        if not open_id_config or not open_id_config.get('issuer'):
            logging.error('Open id config or issuer could not be found.')
            raise AuthenticationFailed('Could not retrieve open id config issuer')

        issuer = open_id_config.get('issuer')
        headers = jwt.get_unverified_header(header_token)

        if 'kid' not in headers:
            logging.error('Error decoding token. Key ID is missing from headers.')
            raise AuthenticationFailed('Key ID is missing from the incoming data')

        jwk_pem = None
        for current_jwk in public_jwks:
            if current_jwk.get('kid') == headers.get('kid'):
                jwk_pem = jwt.PyJWK(current_jwk).key
                break

        if jwk_pem is None:
            logging.error(f'Error decoding token. Key ID ({headers.get("kid")}) is missing from public list.')
            raise AuthenticationFailed('Key ID is missing from the JWK list')

        # Amount of time over what the iat is issued for to allow
        # We were having millisecond timing issues, so this is set to a few seconds to cover for that.
        leeway = datetime.timedelta(seconds=5)
        decoded_jwt = jwt.decode(
            header_token, key=jwk_pem, audience=settings.FXA_CLIENT_ID, algorithms='RS256', leeway=leeway
        )

        # Final verification
        if decoded_jwt.get('iss') != issuer:
            logging.error(f'Issuer is not valid: ({decoded_jwt.get("iss")}) vs ({issuer})')
            raise AuthenticationFailed('Issuer mismatch')

        try:
            user = User.objects.get(fxa_id=decoded_jwt.get('sub'))
        except User.DoesNotExist:
            return None

        # Return user and decoded_jwt for request.user and request.auth
        return user, decoded_jwt


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
