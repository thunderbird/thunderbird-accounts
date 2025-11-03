import enum
from urllib.parse import quote, urljoin

from django.conf import settings
from django.urls import reverse

from thunderbird_accounts.utils.utils import get_absolute_url
from thunderbird_accounts.authentication.reserved import is_reserved


class KeycloakRequiredAction(enum.StrEnum):
    """Required actions, they're defined in the server's provider info.

    Yes these are case sensitive...
    CONFIGURE_TOTP
    webauthn-register-passwordless
    UPDATE_PASSWORD
    TERMS_AND_CONDITIONS
    update_user_locale
    idp_link
    VERIFY_EMAIL
    delete_account
    webauthn-register
    VERIFY_PROFILE
    delete_credential
    CONFIGURE_RECOVERY_AUTHN_CODES
    UPDATE_PROFILE
    """

    CONFIGURE_TOTP = 'CONFIGURE_TOTP'
    CONFIGURE_RECOVERY_AUTHN_CODES = 'CONFIGURE_RECOVERY_AUTHN_CODES'
    DELETE_ACCOUNT = 'delete_account'
    DELETE_CREDENTIAL = 'delete_credential'
    IDP_LINK = 'idp_link'
    TERMS_AND_CONDITIONS = 'TERMS_AND_CONDITIONS'
    UPDATE_PASSWORD = 'UPDATE_PASSWORD'
    UPDATE_PROFILE = 'UPDATE_PROFILE'
    UPDATE_USER_LOCALE = 'update_user_locale'
    VERIFY_EMAIL = 'VERIFY_EMAIL'
    VERIFY_PROFILE = 'VERIFY_PROFILE'
    WEBAUTHN_REGISTER = 'webauthn-register'
    WEBAUTHN_REGISTER_PASSWORDLESS = 'webauthn-register-passwordless'


def is_email_in_allow_list(email: str):
    allow_list = settings.AUTH_ALLOW_LIST
    if not allow_list:
        return True

    return email.endswith(tuple(allow_list.split(',')))

def is_email_reserved(email: str):
    if not is_reserved(email):
        return True

    return email.endswith(tuple(allow_list.split(',')))


def create_aia_url(action: KeycloakRequiredAction):
    """Create a url for a user to start a keycloak flow.
    These flows are defined as actions in KeycloakRequiredAction."""
    redirect_uri = quote(get_absolute_url(reverse('login')))
    return urljoin(
        settings.KEYCLOAK_AIA_ENDPOINT,
        f'?response_type=code'
        f'&client_id={settings.OIDC_RP_CLIENT_ID}'
        f'&kc_action={action.value}'
        f'&redirect_uri={redirect_uri}',
    )
