from enum import Enum
import time

import jwt
from django.conf import settings

from thunderbird_accounts.authentication.middleware import OIDC_ACCESS_TOKEN_KEY, refresh_user_access_token


class AccessTokenExpiry(Enum):
    EXPIRED = 'expired'
    NOT_EXPIRED = 'not_expired'
    UNKNOWN = 'unknown'


class AccessTokenPolicy(Enum):
    REQUIRE_KNOWN_FRESH = 'require_known_fresh'
    FORCE_REFRESH = 'force_refresh'


def get_access_token_expiry(access_token: str) -> AccessTokenExpiry:
    try:
        claims = jwt.decode(access_token, options={'verify_signature': False})
        exp = int(claims['exp'])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return AccessTokenExpiry.UNKNOWN
    if time.time() >= exp - settings.MFA_ACCESS_TOKEN_EXPIRY_LEEWAY_SECONDS:
        return AccessTokenExpiry.EXPIRED
    return AccessTokenExpiry.NOT_EXPIRED


def get_user_access_token(
    request,
    *,
    policy: AccessTokenPolicy = AccessTokenPolicy.REQUIRE_KNOWN_FRESH,
) -> str | None:
    """Return the end user's OIDC access token, refreshing if needed."""
    access_token = request.session.get(OIDC_ACCESS_TOKEN_KEY)
    if policy == AccessTokenPolicy.FORCE_REFRESH:
        return refresh_user_access_token(request)

    expiry = get_access_token_expiry(access_token) if access_token else None

    if access_token:
        if expiry == AccessTokenExpiry.NOT_EXPIRED:
            return access_token

    refreshed_access_token = refresh_user_access_token(request)
    if refreshed_access_token:
        return refreshed_access_token

    return None
