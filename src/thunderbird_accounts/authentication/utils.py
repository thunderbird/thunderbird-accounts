import base64
import secrets
import uuid
from typing import Optional
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.contrib.auth import get_user
from django.http import HttpResponseRedirect
from fxa.errors import ClientError
from fxa.oauth import Client
from itsdangerous import URLSafeTimedSerializer

from thunderbird_accounts.client.models import ClientEnvironment


def create_login_code(client_environment: ClientEnvironment, state: Optional[str] = None):
    """Create a login code for login requests"""
    if not client_environment.is_active:
        return None

    if not state:
        state = secrets.token_hex(64)

    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    return token_serializer.dumps({'uuid': str(client_environment.uuid), 'state': state})


def validate_login_code(token: str):
    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    contents = token_serializer.loads(token, settings.LOGIN_MAX_AGE)

    state = contents.get('state')
    client_env_uuid = uuid.UUID(contents.get('uuid'))
    client_env = ClientEnvironment.objects.get(uuid=client_env_uuid)

    if not client_env or not client_env.is_active or not state:
        return None

    return client_env, state


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
    client_env: ClientEnvironment,
    redirect_to: str | None = None,
    state: str | None = None,
    user_session_id: str | None = None,
) -> HttpResponseRedirect:
    """Handles the return response for logins. Used in callback, and also if the
    user is authenticated already to skip the fxa oauth path."""
    if redirect_to:
        return HttpResponseRedirect(redirect_to)

    path_obj = {}

    if state:
        path_obj['state'] = state

    # Pass the user_session_id for the application requesting it. (We don't need it for internal apps.)
    if client_env.client.name != settings.ADMIN_CLIENT_NAME:
        path_obj['user_session_id'] = base64.urlsafe_b64encode(user_session_id.encode())

    redirect_url = urljoin(client_env.redirect_url, f'?{urlencode(path_obj)}')
    return HttpResponseRedirect(redirect_url)
