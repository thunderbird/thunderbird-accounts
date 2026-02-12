import logging

from rest_framework.decorators import api_view, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication.middleware import AccountsOIDCBackend
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

        return Response(sessions)
    except Exception as e:
        logging.exception(f'Error fetching active sessions: {e}')
        raise ValidationError('Error fetching active sessions')


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
def sign_out_session(request: Request):
    if not request.user.is_authenticated:
        raise NotAuthenticated()

    session_id = request.data.get('session_id')

    if not session_id:
        raise ValidationError('session_id is required')

    oidc_id_token = request.session.get('oidc_id_token')

    if not oidc_id_token:
        raise ValidationError('No oidc_id_token found in session')

    try:
        # Sign out from the Keycloak session
        keycloak_client = KeycloakClient()
        keycloak_client.sign_out_session(session_id)

        # Verify if the request's keycloak session_id matches the one in the ID token
        auth_backend = AccountsOIDCBackend()
        payload = auth_backend.verify_token(oidc_id_token)
        keycloak_session_id = payload.get('sid')

        if not keycloak_session_id:
            raise ValidationError("'sid' claim not found in ID token. Did you enable back-channel logout in Keycloak?")

        if keycloak_session_id == session_id:
            # If so, delete current session data and cookie from Django as well
            request.session.flush()

        return Response({'success': True})

    except Exception as e:
        logging.exception(f'Error signing out session: {e}')
        raise ValidationError('Error signing out session')
