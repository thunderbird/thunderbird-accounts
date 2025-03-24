from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from fxa.oauth import Client
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication import utils
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.permissions import IsClient
from thunderbird_accounts.authentication.serializers import UserProfileSerializer
from thunderbird_accounts.authentication.utils import is_email_in_allow_list
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


@api_view(['POST'])
@permission_classes([IsClient])
def is_in_allow_list(request: Request):
    email = request.data.get('email')

    if not email:
        return JsonResponse({'result': False})

    response = cache.get(f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}')

    # Check if we have their user data in accounts
    if not response:
        try:
            user = User.objects.get(email=email)
            response = user.email == email
        except User.DoesNotExist:
            pass

    # If no user data, then see if their email is on the allow list
    if not response:
        response = is_email_in_allow_list(request.email)

    # Cache the result for 1 day
    cache.set(
        f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}', response, settings.IS_IN_ALLOW_LIST_CACHE_MAX_AGE
    )

    return JsonResponse({'result': response})
