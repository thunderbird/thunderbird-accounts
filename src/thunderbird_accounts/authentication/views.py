from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.crypto import get_random_string
from fxa.errors import ClientError
from fxa.oauth import Client
from fxa.profile import Client as ProfileClient

from thunderbird_accounts.authentication.models import User

# Create your views here.

REDIRECT_KEY = 'fxa_redirect_to'
STATE_KEY = 'fxa_state'


def fxa_start(request: HttpRequest, redirect_to: str|None = None):
    """Initiate the Mozilla Account OAuth dance"""
    state = get_random_string(length=64)

    if redirect_to:
        redirect_to = unquote(redirect_to)

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    url = client.get_redirect_url(state, redirect_uri=settings.FXA_CALLBACK, scope='profile')

    request.session[STATE_KEY] = state
    if redirect_to:
        request.session[REDIRECT_KEY] = redirect_to

    return HttpResponseRedirect(url)


def fxa_logout(request: HttpRequest):
    """Logout of fxa"""
    logout(request)

    return HttpResponseRedirect('/')


def fxa_callback(request: HttpRequest):
    """The user returns from the OAuth sequence to us here, where we will check the state
    retrieve the token, and give them profile information."""
    # Retrieve the state
    state = request.session.get(STATE_KEY)
    if state:
        del request.session[STATE_KEY]

    redirect_to = request.session.get(REDIRECT_KEY)
    if redirect_to:
        del request.session[REDIRECT_KEY]

    if not state or state != request.GET.get('state'):
        return HttpResponse(content=b'Invalid Request', status=500)

    code = request.GET.get('code')

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    token = client.trade_code(code)

    try:
        client.verify_token(token.get('access_token'))
    except ClientError:
        return HttpResponse(content=b'Invalid Response from Mozilla Accounts server.', status=500)

    profile_client = ProfileClient(settings.FXA_PROFILE_SERVER_URL)
    profile = profile_client.get_profile(token.get('access_token'))

    # First look-up by fxa uid
    try:
        user = User.objects.get(fxa_id=profile.get('uid'))
        if user.email != profile.get('email'):
            user.last_used_email = user.email
            user.email = profile.get('email')
            user.save()

    except User.DoesNotExist:
        user = None

    # If that doesn't work, look up by email
    if user is None:
        try:
            user = User.objects.get(email=profile.get('email'))
            user.fxa_id = profile.get('uid')
            user.avatar_url = profile.get('avatar', user.avatar_url)
            user.display_name = profile.get('displayName', profile.get('email').split('@')[0])
            user.save()

        except User.DoesNotExist:
            user = None

    if user is None:
        user = User.objects.create(
            fxa_id=profile.get('uid'),
            email=profile.get('email'),
            last_used_email=profile.get('email'),
            username=profile.get('email'),
            avatar_url=profile.get('avatar'),
            display_name=profile.get('displayName', profile.get('email').split('@')[0]),
        )
        user.save()

    user.refresh_from_db()

    user = authenticate(fxa_id=user.fxa_id, email=user.email)
    login(request, user)

    if redirect_to:
        return HttpResponseRedirect(redirect_to)

    return JsonResponse(model_to_dict(user))
