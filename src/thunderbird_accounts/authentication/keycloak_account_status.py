"""Keycloak side of user access: ``enabled`` and the ``is_active`` user attribute mirror ``UserAccess.can_sign_in``;
the ``is_subscribed`` user attribute mirrors ``UserAccess.has_services``. Both attributes reach services as claims."""

from typing import Optional

from thunderbird_accounts.authentication.account_status import AccountStatusHandler, UserAccess
from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import KeycloakError
from thunderbird_accounts.authentication.models import User

# 'yes' is the encoding an earlier version of update_user_plan_info wrote.
SUBSCRIBED_VALUES = ('true', 'yes')


def _flag(value: bool) -> str:
    return 'true' if value else 'false'


def _is_subscribed(user_data: dict) -> bool:
    values = (user_data.get('attributes') or {}).get('is_subscribed') or []
    return bool(values) and values[0] in SUBSCRIBED_VALUES


def _loses_access(current: Optional[dict], access: UserAccess) -> bool:
    """Whether applying ``access`` takes something away from what Keycloak currently grants. Without the current
    representation any restricted access counts, so an outage cannot leave a session alive."""
    if current is None:
        return not access.can_sign_in or not access.has_services
    return (current.get('enabled', True) and not access.can_sign_in) or (
        _is_subscribed(current) and not access.has_services
    )


class KeycloakAccountStatusHandler(AccountStatusHandler):
    label = 'Keycloak'

    def sync(self, user: User, access: UserAccess) -> None:
        if not user.oidc_id:
            return

        keycloak = KeycloakClient()
        try:
            current = keycloak.get_user(user.oidc_id).json()
        except KeycloakError:
            current = None

        revoke_sessions = _loses_access(current, access)

        # The user is updated before sessions are revoked so a sign-in right after the revocation reads the new
        # attribute.
        update_error = None
        try:
            keycloak.update_user(
                user.oidc_id,
                enabled=access.can_sign_in,
                attributes={
                    'is_active': _flag(access.can_sign_in),
                    'is_subscribed': _flag(access.has_services),
                },
                user_data=current,
            )
        except KeycloakError as ex:
            if not revoke_sessions:
                raise
            update_error = ex

        if not revoke_sessions:
            return

        # Sessions are revoked even if the update failed, so a live session cannot outlast a Keycloak outage.
        try:
            keycloak.logout_user(user.oidc_id)
        except KeycloakError as ex:
            if update_error is None:
                raise
            raise KeycloakError(f'{update_error}; {ex}') from ex

        if update_error is not None:
            raise update_error
