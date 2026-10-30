"""Keycloak side of user access: ``enabled`` mirrors ``UserAccess.can_sign_in``."""

from thunderbird_accounts.authentication.account_status import AccountStatusHandler, UserAccess
from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import KeycloakError
from thunderbird_accounts.authentication.models import User


class KeycloakAccountStatusHandler(AccountStatusHandler):
    label = 'Keycloak'

    def sync(self, user: User, access: UserAccess) -> None:
        if not user.oidc_id:
            return

        keycloak = KeycloakClient()
        if access.can_sign_in:
            keycloak.update_user(user.oidc_id, enabled=True)
            return

        update_error = None
        try:
            keycloak.update_user(user.oidc_id, enabled=False)
        except KeycloakError as ex:
            update_error = ex

        # Sessions are revoked even if disabling failed, so a live session cannot outlast a Keycloak outage.
        try:
            keycloak.logout_user(user.oidc_id)
        except KeycloakError as ex:
            if update_error is None:
                raise
            raise KeycloakError(f'{update_error}; {ex}') from ex

        if update_error is not None:
            raise update_error
