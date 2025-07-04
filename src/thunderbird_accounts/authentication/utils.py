import secrets
import uuid
from typing import Optional

from django.conf import settings
from django.core.cache import caches
from itsdangerous import URLSafeTimedSerializer

from thunderbird_accounts.client.models import ClientEnvironment


def create_login_code(client_environment: ClientEnvironment, state: Optional[str] = None):
    """Create a login code for login requests"""
    if not client_environment.is_active:
        return None

    if not state:
        state = secrets.token_hex(64)

    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    return token_serializer.dumps({'uuid': str(client_environment.uuid), 'state': state})


def validate_login_code(token: str):
    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    contents = token_serializer.loads(token, settings.LOGIN_MAX_AGE_IN_SECONDS)

    state = contents.get('state')
    client_env_uuid = uuid.UUID(contents.get('uuid'))
    client_env = ClientEnvironment.objects.get(uuid=client_env_uuid)

    if not client_env or not client_env.is_active or not state:
        return None

    return client_env, state


def get_cache_allow_list_entry(email: str):
    return caches['default'].get(f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}')


def set_cache_allow_list_entry(email: str, result: bool):
    caches['default'].set(
        f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}', result, settings.IS_IN_ALLOW_LIST_CACHE_MAX_AGE_IN_SECONDS
    )


def delete_cache_allow_list_entry(email: str):
    caches['default'].delete(f'{settings.IS_IN_ALLOW_LIST_CACHE_KEY}:{email}')


def is_email_in_allow_list(email: str):
    allow_list = settings.AUTH_ALLOW_LIST
    if not allow_list:
        return True

    return email.endswith(tuple(allow_list.split(',')))
