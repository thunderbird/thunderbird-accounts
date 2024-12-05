import logging
import uuid
from urllib.parse import unquote, urlencode

from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from django.utils.crypto import get_random_string
from fxa.errors import ClientError
from fxa.oauth import Client
from fxa.profile import Client as ProfileClient
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User, UserSession
from thunderbird_accounts.authentication.utils import (
    validate_login_code,
    handle_auth_callback_response,
    is_already_authenticated,
)
from thunderbird_accounts.client.models import ClientEnvironment

REDIRECT_KEY = 'fxa_redirect_to'
STATE_KEY = 'fxa_state'
CLIENT_ENV_KEY = 'client_uuid'


def fxa_start(request: HttpRequest, login_code: str, redirect_to: str | None = None):
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
        return handle_auth_callback_response(user, client_environment, redirect_to, state)

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    url = client.get_redirect_url(state, redirect_uri=settings.FXA_CALLBACK, scope='profile')

    request.session[STATE_KEY] = state
    request.session[CLIENT_ENV_KEY] = str(client_environment.uuid)
    if redirect_to:
        request.session[REDIRECT_KEY] = redirect_to

    return HttpResponseRedirect(url)


def fxa_logout(request: HttpRequest):
    """Logout of fxa"""

    user = request.user
    if user:
        client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
        try:
            client.destroy_token(user.fxa_token)
        except ClientError:
            logging.debug('Failed to destroy fxa access token')

        user.fxa_token = None
        user.save()

    logout(request)

    return HttpResponseRedirect('/')


def fxa_callback(request: HttpRequest):
    """The user returns from the OAuth sequence to us here, where we will check the state
    retrieve the token, and give them profile information."""

    # Retrieve the client env uuid
    client_env_uuid = request.session.get(CLIENT_ENV_KEY)
    if client_env_uuid:
        del request.session[CLIENT_ENV_KEY]

    # Retrieve the state
    state = request.session.get(STATE_KEY)
    if state:
        del request.session[STATE_KEY]

    # Retrieve a redirect to if available
    redirect_to = request.session.get(REDIRECT_KEY)
    if redirect_to:
        del request.session[REDIRECT_KEY]

    if not state or state != request.GET.get('state') or not client_env_uuid:
        logging.debug('State not found, state did not match session state, or client_env_uuid was not found.')
        return HttpResponse(content=_('Invalid Request'), status=500)

    # Another check to see if the env hasn't been invalidated between the login start and now.
    client_env = ClientEnvironment.objects.get(uuid=uuid.UUID(client_env_uuid))
    if not client_env or not client_env.is_active:
        logging.debug('Failed to find client env')
        return HttpResponse(content=_('Invalid Request'), status=500)

    code = request.GET.get('code')
    is_admin_client = client_env.client.name == settings.ADMIN_CLIENT_NAME
    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    token = client.trade_code(code)

    try:
        client.verify_token(token.get('access_token'))
    except ClientError:
        return HttpResponse(content=_('Invalid Response from Mozilla Accounts server.'), status=500)

    # Retrieve the user's fxa profile
    profile_client = ProfileClient(settings.FXA_PROFILE_SERVER_URL)
    profile = profile_client.get_profile(token.get('access_token'))

    # Try to authenticate with fxa id and email
    user = authenticate(fxa_id=profile.get('uid'), email=profile.get('email'))

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

    # Update the access token too!
    user.fxa_token = token.get('access_token')
    user.save()

    user.refresh_from_db()

    if is_admin_client and not user.is_staff:
        logging.debug(f'Unauthorized user {user.uuid} trying to access admin panel.')
        return HttpResponse('401 Unauthorized', status=401)

    # Login with django auth
    login(request, user)

    # Save the current session key so we can remove it later if they log out.
    UserSession.objects.create(
        user_id=user.uuid,
        session_key=request.session._session_key
    )

    return handle_auth_callback_response(user, client_env, redirect_to, state)
