import base64
import logging
import secrets
import uuid
from typing import Optional
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.http import HttpResponseRedirect
from fxa.errors import ClientError
from fxa.oauth import Client as FxaOAuthClient
from itsdangerous import URLSafeTimedSerializer

from thunderbird_accounts.authentication.const import USER_SESSION_CACHE_KEY
from thunderbird_accounts.authentication.models import User, UserSession
from thunderbird_accounts.authentication.serializers import UserCacheSerializer
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

        client = FxaOAuthClient(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
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


def get_cache_session(session_key: str):
    return caches['shared'].get(f'{USER_SESSION_CACHE_KEY}.{session_key}')


def delete_cache_session(user_session: UserSession):
    """Delete the cache session associated with a user session"""
    return caches['shared'].delete(f'{USER_SESSION_CACHE_KEY}.{user_session.session_key}')


def save_cache_session(user_session: UserSession):
    """Create and save a cache session associated with a user session"""
    user_obj = UserCacheSerializer(user_session.user).data
    return caches['shared'].set(f'{USER_SESSION_CACHE_KEY}.{user_session.session_key}', user_obj)


def get_cache_allow_list_entry(email: str):
    return caches['default'].get(f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}')


def set_cache_allow_list_entry(email: str, result: bool):
    caches['default'].set(
        f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}', result, settings.IS_IN_ALLOW_LIST_CACHE_MAX_AGE
    )


def delete_cache_allow_list_entry(email: str):
    caches['default'].delete(f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}')


def logout_user(user: User, client: Optional[FxaOAuthClient] = None) -> bool:
    """Log out a user by:
    1. Telling FXA to delete their access token
    2. Removing the access token from the user object (and saving)
    3. Looping through each user session associated with the user
        - Deleting the Django Session via saved `UserSession.session_key` (Django Auth)
        - Deleting the User Session (Our Auth / DB)
        - Deleting the User Session object in our cache (Our Auth / Redis)
    4. Fin!
    """
    if not client:
        client = FxaOAuthClient(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)

    try:
        if user.fxa_token:
            client.destroy_token(user.fxa_token)
    except ClientError as ex:
        logging.error(f'Could not destroy fxa token on logout. Reason: {ex.details} / {ex.error}')
        return False

    # Remove the token too!
    user.fxa_token = None
    user.save()

    for user_session in user.usersession_set.all():
        try:
            session = Session.objects.get(session_key=user_session.session_key)
            # Delete the session
            session.delete()
        except Session.DoesNotExist:
            pass

        # And also the user session
        user_session.delete()
        delete_cache_session(user_session)

    return True


def is_email_in_allow_list(email: str):
    allow_list = settings.FXA_ALLOW_LIST
    if not allow_list:
        return True

    return email.endswith(tuple(allow_list.split(',')))
