from django.conf import settings
from django.contrib.auth import logout, update_session_auth_hash
from django.http import JsonResponse
from django.urls import reverse
from fxa.oauth import Client
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication import utils
from thunderbird_accounts.authentication.permissions import IsClient
from thunderbird_accounts.authentication.serializers import UserProfileSerializer
from thunderbird_accounts.utils.utils import get_absolute_url


@api_view(['POST'])
@permission_classes([IsClient])
def get_login_code(request: Request):
    state = request.data.get('state')
    client_env = request.client_env
    login_code = utils.create_login_code(client_env, state)
    login_url = get_absolute_url(reverse('fxa_login', kwargs={'login_code': login_code}))
    return JsonResponse(
        {
            'state': state,
            'login': login_url,
        }
    )


@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)


@api_view(['POST'])
def logout_user(request: Request):
    """Logs out an authenticated user (via jwt), destroys the fxa token and logs out the user's session"""
    if not request.user:
        raise NotAuthenticated()
    fxa_token = request.user.fxa_token
    client = Client(settings.FXA_CLIENT_ID, settings.FXA_SECRET, settings.FXA_OAUTH_SERVER_URL)
    client.destroy_token(fxa_token)

    # Custom logout routine
    request.user.logout()

    return JsonResponse({'success': True})
