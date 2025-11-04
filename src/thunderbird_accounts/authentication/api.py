from rest_framework.decorators import api_view, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, ValidationError
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

    try:
        keycloak_client = KeycloakClient()
        sessions = keycloak_client.get_active_sessions(request.user.oidc_id)

        # Print all keys from request.session
        print(request.session.keys())
        print(request.session.items())
        print(request.session.values())
        print(request.session.get('session_id'))
        print(request.session.get('session_key'))
        print(request.session.get('session_data'))
        print(request.session.get('session_expiry'))
        print(request.session.get('session_created'))
        print(request.session.get('session_updated'))
        return Response(sessions)
    except Exception as e:
        raise ValidationError(f'Error fetching active sessions: {e}')


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
def sign_out_session(request: Request):
    if not request.user.is_authenticated:
        raise NotAuthenticated()

    session_id = request.data.get('session_id')

    if not session_id:
        raise ValidationError('session_id is required')

    try:
        keycloak_client = KeycloakClient()
        return Response(keycloak_client.sign_out_session(session_id))
    except Exception as e:
        raise ValidationError(f'Error signing out session: {e}')
