import time

from django.conf import settings


KEYCLOAK_OTP_CREDENTIAL_TYPE = 'otp'
KEYCLOAK_RECOVERY_CODES_CREDENTIAL_TYPE = 'recovery-authn-codes'
MFA_MANAGEMENT_AUTH_SESSION_KEY = 'mfa_management_auth_time'
MFA_REAUTH_PENDING_SESSION_KEY = 'mfa_reauth_pending'
PENDING_TOTP_CACHE_KEY = 'accounts:mfa:totp-setup:{user_id}'


def make_pending_totp_cache_key(user_id: int) -> str:
    return PENDING_TOTP_CACHE_KEY.format(user_id=user_id)


def has_recent_mfa_management_auth(session) -> bool:
    auth_time = session.get(MFA_MANAGEMENT_AUTH_SESSION_KEY)
    if auth_time is None:
        return False

    try:
        return int(time.time()) - int(auth_time) <= settings.MFA_RECENT_AUTH_SECONDS
    except (TypeError, ValueError):
        return False
