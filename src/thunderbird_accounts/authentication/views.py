import logging
import uuid
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse, JsonResponse
from django.utils.crypto import get_random_string
from fxa.errors import ClientError
from fxa.oauth import Client
from fxa.profile import Client as ProfileClient
from rest_framework_simplejwt.tokens import RefreshToken

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import validate_login_code
from thunderbird_accounts.client.models import ClientEnvironment

REDIRECT_KEY = 'fxa_redirect_to'
STATE_KEY = 'fxa_state'
CLIENT_ENV_KEY = 'client_uuid'


def fxa_start(request: HttpRequest, login_code: str, redirect_to: str|None = None):
    """Initiate the Mozilla Account OAuth dance"""
    client_environment = validate_login_code(login_code)

    if not client_environment:
        return HttpResponse('401 Unauthorized', status=401)

    state = get_random_string(length=64)

    if redirect_to:
        redirect_to = unquote(redirect_to)

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    url = client.get_redirect_url(state, redirect_uri=settings.FXA_CALLBACK, scope='profile')

    request.session[STATE_KEY] = state
    request.session[CLIENT_ENV_KEY] = client_environment.uuid.hex
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
            logging.debug("Failed to destroy fxa access token")

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

    redirect_to = request.session.get(REDIRECT_KEY)
    if redirect_to:
        del request.session[REDIRECT_KEY]

    if not state or state != request.GET.get('state') or not client_env_uuid:
        return HttpResponse(content=b'Invalid Request', status=500)

    code = request.GET.get('code')

    # Another check to see if the env hasn't been invalidated between the login start and now.
    client_env = ClientEnvironment.objects.get(uuid=uuid.UUID(client_env_uuid))
    if not client_env or not client_env.is_active:
        return HttpResponse(content=b'Invalid Request, Client Environment not found or not active', status=500)

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    token = client.trade_code(code)

    try:
        client.verify_token(token.get('access_token'))
    except ClientError:
        return HttpResponse(content=b'Invalid Response from Mozilla Accounts server.', status=500)

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

    # Login with django auth
    login(request, user)

    if redirect_to:
        return HttpResponseRedirect(redirect_to)

    # Create an access token as well - only for non-redirect routes
    refresh = RefreshToken.for_user(user)
    return HttpResponseRedirect(f'{client_env.redirect_url}?token={refresh}')
