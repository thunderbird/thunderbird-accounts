import uuid

from django.conf import settings
from itsdangerous import URLSafeTimedSerializer

from thunderbird_accounts.client.models import ClientEnvironment


def create_login_code(client_environment: ClientEnvironment):
    """Create a login code for login requests"""
    if not client_environment.is_active:
        return None

    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    return token_serializer.dumps({'uuid': client_environment.uuid.hex})


def validate_login_code(token: str):
    token_serializer = URLSafeTimedSerializer(settings.LOGIN_CODE_SECRET, 'login')
    contents = token_serializer.loads(token, settings.LOGIN_MAX_AGE)

    client_env_uuid = uuid.UUID(contents.get('uuid'))
    client_env = ClientEnvironment.objects.get(uuid=client_env_uuid)

    if not client_env or not client_env.is_active:
        return None

    return client_env
