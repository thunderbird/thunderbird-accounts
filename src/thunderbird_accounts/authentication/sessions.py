"""Keycloak session handling for the security settings views."""

import logging
import re
from typing import TYPE_CHECKING

import jwt
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

if TYPE_CHECKING:
    from thunderbird_accounts.authentication.clients import KeycloakAccountClient

# Keycloak session ids are UUIDs (pre-26) or unpadded base64url strings (26+).
KEYCLOAK_SESSION_ID_RE = re.compile(r'[A-Za-z0-9_-]{1,128}')


def current_session_id(request: Request) -> str | None:
    """The Keycloak session id behind the request's own sign-in, read from its access token."""
    access_token = request.session.get('oidc_access_token')
    if not access_token:
        return None

    try:
        return jwt.decode(access_token, options={'verify_signature': False}).get('sid')
    except (jwt.PyJWTError, TypeError):
        return None


def mark_current_session(request: Request, sessions: list[dict]) -> list[dict]:
    """Modify sessions list to mark current one with is_current key"""
    session_id = current_session_id(request)

    if not session_id:
        for session in sessions:
            session['is_current'] = False
        return sessions

    for session in sessions:
        session['is_current'] = session.get('id') == session_id

    return sessions


def sign_out_keycloak_session(
    request: Request, keycloak_client: 'KeycloakAccountClient', user_access_token: str, session_id: str
) -> bool:
    """Sign out one Keycloak session, flushing the Django session too when it is the current one.

    Returns whether the current session was signed out. Ids outside Keycloak's alphabet are
    rejected before they are interpolated into the Account API path.
    """
    if not isinstance(session_id, str) or not KEYCLOAK_SESSION_ID_RE.fullmatch(session_id):
        raise ValidationError('session_id is not a valid Keycloak session id')

    keycloak_client.sign_out_session(user_access_token, session_id)

    if current_session_id(request) == session_id:
        request.session.flush()
        return True
    return False


def revoke_connected_app_access(
    request: Request, keycloak_client: 'KeycloakAccountClient', user_access_token: str, client_id: str
) -> bool:
    """Disconnect an app on every device.

    Revoking the client's consent drops its offline tokens but leaves any browser sign-in the
    app came from alive, and that sign-in can hand the app a new offline token without showing a
    login form. Every Keycloak session that holds a client session for the app is therefore signed
    out as well. Returns whether the request's own session was among them; the caller's Django
    session is flushed in that case.
    """
    session_ids = keycloak_client.get_connected_app_session_ids(user_access_token, client_id)
    keycloak_client.revoke_client_consent(user_access_token, client_id)

    # The caller's access token dies with its own session, so that one has to go last.
    own_session_id = current_session_id(request)
    session_ids.sort(key=lambda session_id: session_id == own_session_id)
    signed_out_current_session = False
    for session_id in session_ids:
        if not isinstance(session_id, str) or not KEYCLOAK_SESSION_ID_RE.fullmatch(session_id):
            logging.warning(
                f'[revoke_connected_app_access] Skipping session id with unexpected characters: {session_id!r}'
            )
            continue
        keycloak_client.sign_out_session(user_access_token, session_id)
        if session_id == own_session_id:
            signed_out_current_session = True

    if signed_out_current_session:
        request.session.flush()
    return signed_out_current_session
