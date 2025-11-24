from typing import Optional
from django.test import Client as RequestClient

from requests import Response

from thunderbird_accounts.authentication.models import User


def oidc_force_login(client: RequestClient, user: User, backend=None):
    """This works like :any:`django.test.Client` except it also bypasses the missing
    ``oidc_id_token_expiration`` session value by setting it in the far future.

    Other-wise the request would be redirected to keycloak to login."""
    client.force_login(user, backend=backend)

    # Mock OIDC session data to prevent SessionRefresh middleware from redirecting
    session = client.session
    session['oidc_id_token_expiration'] = 9999999999  # Far future timestamp
    session.save()


def build_keycloak_success_response(return_json: Optional[dict] = None, return_headers: Optional[dict] = None):
    """Builds an empty successful keycloak request response."""
    fake_response = Response()
    fake_response.status_code = 200
    fake_response.headers = return_headers or {}
    fake_response.json = lambda: return_json or {}
    return fake_response


def build_mail_get_account(return_json: Optional[dict] = None, return_headers: Optional[dict] = None):
    """Builds a successful stalwart get account request response."""
    default_return = {
        'data': {
            'id': 1,
            'name': 'user@example.org',
            'type': 'individual',
            'description': 'Example User',
            'emails': ['user@example.org'],
            'roles': ['user'],
            'quota': 0,
        }
    }

    fake_response = Response()
    fake_response.status_code = 200
    fake_response.headers = return_headers or {}
    fake_response.json = lambda: return_json or default_return
    return fake_response


def build_mail_update_account(return_json: Optional[dict] = None, return_headers: Optional[dict] = None):
    """Builds a successful stalwart update account request response."""
    fake_response = Response()
    fake_response.status_code = 200
    fake_response.headers = return_headers
    fake_response.json = lambda: return_json or {}
    return fake_response
