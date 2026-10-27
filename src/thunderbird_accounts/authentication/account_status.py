"""Activate and deactivate users across Django, Keycloak and Stalwart."""

import logging

import sentry_sdk

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import KeycloakError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient


def set_user_active(user: User, active: bool) -> list[str]:
    """Persist ``is_active`` and mirror it to Keycloak and Stalwart.

    Django's ``is_active`` is the source of truth; Keycloak's ``enabled`` flag and the Stalwart account's permissions
    are derived from it. Deactivating also signs the user out of every Keycloak session. The local change is kept even
    when an external service fails; those failures are returned as messages.
    """
    errors = []

    user.is_active = active
    user.save(update_fields=['is_active', 'updated_at'])

    if user.oidc_id:
        keycloak = KeycloakClient()
        try:
            keycloak.update_user(user.oidc_id, enabled=active)
        except KeycloakError as ex:
            sentry_sdk.capture_exception(ex)
            errors.append(f'Keycloak: {ex}')
        # Revoke sessions even if disabling failed, so a live session cannot outlast a Keycloak outage.
        if not active:
            try:
                keycloak.logout_user(user.oidc_id)
            except KeycloakError as ex:
                sentry_sdk.capture_exception(ex)
                errors.append(f'Keycloak: {ex}')

    primary_email = user.stalwart_primary_email
    if primary_email:
        try:
            MailClient().set_account_active(primary_email, active)
            user.account_set.update(active=active)
        except Exception as ex:
            sentry_sdk.capture_exception(ex)
            errors.append(f'Stalwart: {ex}')

    if errors:
        logging.warning(f'[set_user_active] is_active={active} for user {user.uuid} had errors: {errors}')

    return errors
