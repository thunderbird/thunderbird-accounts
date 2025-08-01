import logging
from socket import gethostbyname, gethostname

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from .models import User
from .utils import is_email_in_allow_list

from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class AccountsOIDCBackend(OIDCAuthenticationBackend):
    def _check_allow_list(self, claims: dict):
        email = claims.get('email', '')
        email_verified = claims.get('email_verified')

        if not settings.IS_DEV and (not email_verified or not is_email_in_allow_list(email)):
            logging.warning(f"Denied user {email} as they're not in the allow list.")
            raise PermissionDenied()

        return True

    def _set_user_fields(self, user: User, claims: dict):
        print('User -> ', user)
        print('Claims -> ', claims)

        # Standard OpenID connect fields
        user.oidc_id = claims.get('sub')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.timezone = claims.get('zoneinfo', 'UTC')
        user.avatar_url = claims.get('picture')
        user.display_name = claims.get('preferred_username')
        user.username = claims.get('preferred_username')

        # Non-standard
        user.is_staff = claims.get('is_services_admin', 'no').lower() == 'yes'
        user.is_superuser = claims.get('is_services_admin', 'no').lower() == 'yes'

        return user

    def create_user(self, claims):
        self._check_allow_list(claims)

        user = super().create_user(claims)
        user = self._set_user_fields(user, claims)
        user.save()

        return user

    def update_user(self, user, claims):
        self._check_allow_list(claims)

        user = self._set_user_fields(user, claims)

        # Update the email if it has changed
        user.last_used_email = user.email
        if claims.get('email') and user.email != claims.get('email'):
            user.email = claims.get('email')
        user.save()

        return user

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified oidc_id."""
        sub = claims.get('sub')
        if not sub:
            return self.UserModel.objects.none()

        user_query = self.UserModel.objects.filter(oidc_id__iexact=sub)

        # Fallback to matching by email if the env is set
        if settings.OIDC_FALLBACK_MATCH_BY_EMAIL:
            if user_query.count() == 0:
                user_query = self.UserModel.objects.filter(email__iexact=claims.get('email'))
        return user_query


class SetHostIPInAllowedHostsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        allowed_hosts = settings.ALLOWED_HOSTS

        # Get the IP of whatever machine is running this code and allow it as a hostname
        hostname = gethostbyname(gethostname())
        if hostname not in allowed_hosts:
            allowed_hosts.append(hostname)

        # Set both django allowed hosts and cors allowed origins
        settings.ALLOWED_HOSTS = allowed_hosts

        response = self.get_response(request)

        return response
