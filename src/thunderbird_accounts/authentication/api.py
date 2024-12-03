from django.http import JsonResponse
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
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
    return Response(UserProfileSerializer(request.user).data)
