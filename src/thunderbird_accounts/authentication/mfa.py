import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import quote, urlencode

from django.conf import settings


KEYCLOAK_OTP_CREDENTIAL_TYPE = 'otp'
KEYCLOAK_RECOVERY_CODES_CREDENTIAL_TYPE = 'recovery-authn-codes'
MFA_MANAGEMENT_AUTH_SESSION_KEY = 'mfa_management_auth_time'
MFA_REAUTH_PENDING_SESSION_KEY = 'mfa_reauth_pending'
PENDING_TOTP_CACHE_KEY = 'accounts:mfa:totp-setup:{user_id}'
PENDING_RECOVERY_CODES_CACHE_KEY = 'accounts:mfa:recovery-codes-setup:{user_id}'
TOTP_SECRET_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

# Matches Keycloak's RecoveryAuthnCodesUtils alphabet so codes generated here
# are visually consistent with Keycloak-generated codes (no `O`, no `0`).
RECOVERY_CODE_ALPHABET = 'ABCDEFGHIJKLMNPQRSTUVWXYZ123456789'


def create_totp_secret() -> str:
    return ''.join(secrets.choice(TOTP_SECRET_ALPHABET) for _ in range(settings.MFA_TOTP_SECRET_LENGTH))


def encode_totp_secret(secret: str) -> str:
    return base64.b32encode(secret.encode()).decode().rstrip('=')


def format_totp_secret(secret: str) -> str:
    encoded_secret = encode_totp_secret(secret)
    return ' '.join(encoded_secret[index : index + 4] for index in range(0, len(encoded_secret), 4))


def create_otpauth_uri(secret: str, account_name: str) -> str:
    issuer = settings.MFA_TOTP_ISSUER
    label = quote(f'{issuer}:{account_name}')
    query = urlencode(
        {
            'secret': encode_totp_secret(secret),
            'issuer': issuer,
            'algorithm': settings.MFA_TOTP_ALGORITHM_KEY,
            'digits': settings.MFA_TOTP_DIGITS,
            'period': settings.MFA_TOTP_PERIOD,
        }
    )
    return f'otpauth://totp/{label}?{query}'


def make_totp_code(secret: str, for_time: int | None = None) -> str:
    if for_time is None:
        for_time = int(time.time())

    counter = int(for_time / settings.MFA_TOTP_PERIOD)
    digest = hmac.new(secret.encode(), counter.to_bytes(8, 'big'), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated_hash = int.from_bytes(digest[offset : offset + 4], 'big') & 0x7FFFFFFF
    code = truncated_hash % (10**settings.MFA_TOTP_DIGITS)
    return str(code).zfill(settings.MFA_TOTP_DIGITS)


def validate_totp_code(secret: str, code: str) -> bool:
    normalized_code = code.strip().replace(' ', '')
    if not normalized_code.isdigit() or len(normalized_code) != settings.MFA_TOTP_DIGITS:
        return False

    current_time = int(time.time())
    for window_offset in range(-settings.MFA_TOTP_LOOK_AHEAD_WINDOW, settings.MFA_TOTP_LOOK_AHEAD_WINDOW + 1):
        window_time = current_time + (window_offset * settings.MFA_TOTP_PERIOD)
        if hmac.compare_digest(make_totp_code(secret, window_time), normalized_code):
            return True

    return False


def make_pending_totp_cache_key(user_id: int) -> str:
    return PENDING_TOTP_CACHE_KEY.format(user_id=user_id)


def make_pending_recovery_codes_cache_key(user_id: int) -> str:
    return PENDING_RECOVERY_CODES_CACHE_KEY.format(user_id=user_id)


def generate_recovery_codes() -> list[str]:
    return [
        ''.join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(settings.MFA_RECOVERY_CODE_LENGTH))
        for _ in range(settings.MFA_RECOVERY_CODE_COUNT)
    ]


def hash_recovery_code(raw_code: str) -> str:
    """Hash a raw recovery code so Keycloak's RecoveryAuthnCodesFormAuthenticator can verify it."""
    digest = hashlib.sha512(raw_code.encode()).digest()
    return base64.b64encode(digest).decode()


def has_recent_mfa_management_auth(session) -> bool:
    auth_time = session.get(MFA_MANAGEMENT_AUTH_SESSION_KEY)
    if auth_time is None:
        return False

    try:
        return int(time.time()) - int(auth_time) <= settings.MFA_RECENT_AUTH_SECONDS
    except (TypeError, ValueError):
        return False
