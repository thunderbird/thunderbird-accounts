import logging
import uuid
from typing import Optional
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.core.cache import caches
from django.http import HttpResponseRedirect, HttpResponse
from fxa.errors import ClientError
from fxa.oauth import Client
from fxa.profile import Client as ProfileClient
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication.const import USER_SESSION_CACHE_KEY
from thunderbird_accounts.authentication.models import User, UserSession
from thunderbird_accounts.authentication.permissions import IsValidFXAWebhook
from thunderbird_accounts.authentication.utils import (
    validate_login_code,
    handle_auth_callback_response,
    is_already_authenticated,
    save_cache_session,
    logout_user,
)
from thunderbird_accounts.client.models import ClientEnvironment
from thunderbird_accounts.utils.types import AccountsHttpRequest


REDIRECT_KEY = 'fxa_redirect_to'
STATE_KEY = 'fxa_state'
CLIENT_ENV_KEY = 'client_uuid'


def _set_user_session(request: AccountsHttpRequest, user: User):
    """Create or Updates a UserSession, and sets a cache entry."""
    session_key = request.session._session_key

    # Save the current session key so we can remove it later if they log out.
    user_session, created = UserSession.objects.update_or_create(user_id=user.uuid, session_key=session_key)

    return save_cache_session(user_session)


def _create_or_update_user(profile: dict, user: Optional[User] = None):
    """Creates a user from a given fxa profile dict or updates a users avatar and displayName (if not already set.)"""
    if user is None:
        # New user flow:
        user = User.objects.create(
            fxa_id=profile.get('uid'),
            email=profile.get('email'),
            last_used_email=profile.get('email'),
            username=profile.get('email'),
            avatar_url=profile.get('avatar'),
            display_name=profile.get('displayName', profile.get('email').split('@')[0]),
        )
    else:
        # Update avatar and display name if available
        user.avatar_url = profile.get('avatar', user.avatar_url)
        if not user.display_name:
            user.display_name = profile.get('displayName', profile.get('email').split('@')[0])
    return user


def fxa_start(request: AccountsHttpRequest, login_code: str, redirect_to: str | None = None):
    """Initiate the Mozilla Account OAuth dance"""
    client_environment, state = validate_login_code(login_code)

    if not client_environment:
        return HttpResponse(_('401 Unauthorized'), status=401)

    if redirect_to:
        redirect_to = unquote(redirect_to)

    # If the user is authenticated then we can skip the fxa login process
    if is_already_authenticated(request):
        user = request.user
        logging.debug('Already logged in, skipping oauth')

        _set_user_session(request, user)

        return handle_auth_callback_response(client_environment, redirect_to, state, request.session._session_key)

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    url = client.get_redirect_url(state, redirect_uri=settings.FXA_CALLBACK, scope='profile')

    request.session[STATE_KEY] = state
    request.session[CLIENT_ENV_KEY] = str(client_environment.uuid)
    if redirect_to:
        request.session[REDIRECT_KEY] = redirect_to

    return HttpResponseRedirect(url)


def fxa_logout(request: AccountsHttpRequest):
    """Logout of fxa"""

    user = request.user
    session_key = request.session._session_key
    if user:
        client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
        try:
            client.destroy_token(user.fxa_token)
        except ClientError:
            logging.debug('Failed to destroy fxa access token')

        user.fxa_token = None
        user.save()

        # Delete any db sessions
        UserSession.objects.filter(user_id=user.uuid, session_key=session_key).delete()

    # Clear the cached entry
    caches['shared'].delete(f'{USER_SESSION_CACHE_KEY}.{session_key}')

    logout(request)

    return HttpResponseRedirect('/')


def fxa_callback(request: AccountsHttpRequest):
    """The user returns from the OAuth sequence to us here, where we will check the state
    retrieve the token, and give them profile information."""

    # Retrieve the client env uuid
    client_env_uuid = request.session.pop(CLIENT_ENV_KEY, None)

    # Retrieve the state
    state = request.session.pop(STATE_KEY, None)

    # Retrieve a redirect to if available
    redirect_to = request.session.pop(REDIRECT_KEY, None)

    if not state or state != request.GET.get('state') or not client_env_uuid:
        logging.debug('State not found, state did not match session state, or client_env_uuid was not found.')
        return HttpResponse(content=_('Invalid Request'), status=500)

    # Another check to see if the env hasn't been invalidated between the login start and now.
    client_env = ClientEnvironment.objects.get(uuid=uuid.UUID(client_env_uuid))
    if not client_env or not client_env.is_active:
        logging.debug('Failed to find client env')
        return HttpResponse(content=_('Invalid Request'), status=500)

    code = request.GET.get('code')
    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    token = client.trade_code(code)

    try:
        client.verify_token(token.get('access_token'))
    except ClientError:
        return HttpResponse(content=_('Invalid Response from Mozilla Accounts server.'), status=500)

    # Retrieve the user's fxa profile
    profile_client = ProfileClient(settings.FXA_PROFILE_SERVER_URL)
    profile = profile_client.get_profile(token.get('access_token'))

    profile_email = profile.get('email')
    allow_list = settings.FXA_ALLOW_LIST

    if allow_list and not profile_email.endswith(tuple(allow_list.split(','))):
        return HttpResponse(content=_('You are not allowed to sign-in.'), status=500)

    # Try to authenticate with fxa id and email
    user = authenticate(fxa_id=profile.get('uid'), email=profile.get('email'))
    user = _create_or_update_user(profile, user)

    # Update the access token too!
    user.fxa_token = token.get('access_token')
    user.save()

    user.refresh_from_db()

    # Login with django auth
    login(request, user)

    _set_user_session(request, user)

    return handle_auth_callback_response(client_env, redirect_to, state, request.session._session_key)


@api_view(['POST'])
@authentication_classes([IsValidFXAWebhook])
def fxa_webhook(request: Request):
    """Main for webhooks regarding fxa"""
    response = HttpResponse(content=_('Thank you!'), status=200)

    if not request.auth or not request.user:
        logging.warning('FXA webhook event received for non-existent user.')
        return response

    user = request.user
    events = request.auth.get('events', {})

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)

    for event, event_data in events.items():
        match event:
            case 'https://schemas.accounts.firefox.com/event/password-change':
                # Ensure we ignore out of date requests, also .timestamp() returns seconds, but we get the time in ms.
                token_last_updated = user.last_login.timestamp()
                if token_last_updated > event_data.get('changeTime'):
                    logging.info('Ignoring out of date logout request.')
                    break

                logout_user(user, client)
            case 'https://schemas.accounts.firefox.com/event/profile-change':
                if event_data.get('email') is not None:
                    # Update the user's email, we do this first in case there's a problem with get_profile()
                    user.email = event_data.get('email').lower()
                    user.save()

                # This should just update the profile
                # _create_or_update_user(profile, user)

                # Finally log the subscriber out
                logout_user(user, client)
            case 'https://schemas.accounts.firefox.com/event/delete-user':
                # TODO: Add client webhook here
                logout_user(user, client)
                user.delete()
            case _:
                logging.warning(f'Ignoring event {event}')

    return response
