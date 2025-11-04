from rest_framework.decorators import api_view, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication.serializers import UserProfileSerializer
from thunderbird_accounts.authentication.clients import KeycloakClient

@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication])
def get_active_sessions(request: Request):
    if not request.user.is_authenticated:
        raise NotAuthenticated()
    return Response(KeycloakClient().get_active_sessions(request.user.oidc_id))
