import uuid

from django.conf import settings
from django.contrib.auth import get_user
from django.http import HttpResponseRedirect
from fxa.errors import ClientError
from fxa.oauth import Client
from itsdangerous import URLSafeTimedSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.client.models import ClientEnvironment


def create_login_code(client_environment: ClientEnvironment):
    """Create a login code for login requests"""
    if not client_environment.is_active:
        return None

    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    return token_serializer.dumps({'uuid': client_environment.uuid.hex})


def validate_login_code(token: str):
    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    contents = token_serializer.loads(token, settings.LOGIN_MAX_AGE)

    client_env_uuid = uuid.UUID(contents.get('uuid'))
    client_env = ClientEnvironment.objects.get(uuid=client_env_uuid)

    if not client_env or not client_env.is_active:
        return None

    return client_env


def is_already_authenticated(request):
    """Check if the user is already logged in, and if we're using fxa
    then ensure the token exists and is valid."""
    user = get_user(request)
    if user.is_anonymous:
        return False

    # See if the fxa_token is still good
    if settings.AUTH_SCHEME == 'fxa':
        if not user.fxa_token:
            return False

        client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
        try:
            client.verify_token(user.fxa_token)
        except ClientError:
            return False

    return True


def handle_auth_callback_response(
    user: User, client_env: ClientEnvironment, redirect_to: str | None = None
) -> HttpResponseRedirect:
    """Handles the return response for logins. Used in callback, and also if the
    user is authenticated already to skip the fxa oauth path."""
    if redirect_to:
        return HttpResponseRedirect(redirect_to)

    # Create an access token as well - only for non-redirect routes / non-admin route
    if client_env.client.name == settings.ADMIN_CLIENT_NAME:
        refresh = ''
    else:
        refresh = RefreshToken.for_user(user)
        refresh = f'?token={refresh}'

    return HttpResponseRedirect(f'{client_env.redirect_url}{refresh}')
