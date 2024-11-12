from django.conf import settings
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse, JsonResponse
from django.utils.crypto import get_random_string
from fxa.errors import ClientError
from fxa.oauth import Client
from fxa.profile import Client as ProfileClient


# Create your views here.

STATE_KEY = 'fxa_state'


def fxa_start(request: HttpRequest):
    """Initiate the Mozilla Account OAuth dance"""
    state = get_random_string(length=64)

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    url = client.get_redirect_url(state, redirect_uri=settings.FXA_CALLBACK, scope='profile')

    request.session[STATE_KEY] = state
    return HttpResponseRedirect(url)


def fxa_callback(request: HttpRequest):
    """The user returns from the OAuth sequence to us here, where we will check the state
    retrieve the token, and give them profile information."""
    # Retrieve the state
    state = request.session.get(STATE_KEY)
    if state:
        del request.session[STATE_KEY]

    if not state or state != request.GET.get('state'):
        return HttpResponse(content=b'Invalid Request', status=500)

    code = request.GET.get('code')

    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    token = client.trade_code(code)

    try:
        profile = client.verify_token(token.get('access_token'))
    except ClientError:
        return HttpResponse(content=b'Invalid Response from Mozilla Accounts server.', status=500)

    print(token)
    print(profile)
    profile_client = ProfileClient(settings.FXA_PROFILE_SERVER_URL)
    profile = profile_client.get_profile(token.get('access_token'))

    return JsonResponse(profile)

