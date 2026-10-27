"""Django REST Framework authentication classes."""

from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework import exceptions


class ActiveUserOIDCAuthentication(OIDCAuthentication):
    """Bearer-token authentication that also refuses deactivated users.

    The upstream class resolves the token to a local user without checking ``is_active``; the session backend's
    ``get_user`` does check it, so this keeps the two entry points consistent."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and not result[0].is_active:
            raise exceptions.AuthenticationFailed('User is inactive')
        return result
