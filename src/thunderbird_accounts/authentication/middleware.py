import logging
from typing import Optional
from socket import gethostbyname, gethostname

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .models import User
from .utils import is_email_in_allow_list

from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class AccountsOIDCBackend(OIDCAuthenticationBackend):
    """User authentication middleware for OIDC

    This is our slightly customized mozilla-django-oidc middleware used to create/update/authenticate users
    against oidc flows.
    """

    def get_user(self, user_id):
        """Retrieve the user from OIDC get_user and additionally check if they're active.
        Fixes https://github.com/mozilla/mozilla-django-oidc/issues/520
        """
        user: Optional[User] = super().get_user(user_id)
        return user if self.user_can_authenticate(user) else None

    def _check_allow_list(self, claims: dict):
        email = claims.get('email', '')
        email_verified = claims.get('email_verified')

        # Ignore allow list for services admin
        is_services_admin: bool = claims.get('is_services_admin', 'no') == 'yes'
        if is_services_admin:
            return True

        if not email_verified or not is_email_in_allow_list(email):
            logging.warning(f"Denied user {email} as they're not in the allow list.")
            messages.error(
                self.request,
                _('You are not on the allow list. If you think this is a mistake, please contact support.'),
            )
            raise PermissionDenied()

        return True

    def _set_user_fields(self, user: User, claims: dict):
        # Standard OpenID connect fields
        user.oidc_id = claims.get('sub')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.timezone = claims.get('zoneinfo', 'UTC')
        user.avatar_url = claims.get('picture')
        user.display_name = claims.get('preferred_username')
        user.username = claims.get('preferred_username')

        # Non-standard, only adjust the value if it comes not undefined / null
        is_services_admin = claims.get('is_services_admin')
        if is_services_admin is not None:
            user.is_staff = is_services_admin == 'yes'
            user.is_superuser = is_services_admin == 'yes'

        return user

    def create_user(self, claims):
        self._check_allow_list(claims)

        user = super().create_user(claims)
        user = self._set_user_fields(user, claims)
        user.save()

        # Refresh so we have access to the uuid
        user.refresh_from_db()

        return user

    def update_user(self, user, claims):
        if not user.is_active:
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
            if len(user_query) == 0:
                user_query = self.UserModel.objects.filter(email__iexact=claims.get('email')).order_by('created_at')

                # Remove any weird duplicate accounts
                # See issue #236 for context
                if len(user_query) > 1:
                    to_remove = user_query[1:]
                    logging.warning(
                        f'[AccountsOIDCBackend.filter_users_by_claims] Deleting {len(to_remove)} duplicate accounts!'
                    )
                    for user in to_remove:
                        user.delete()

                # Select the first account
                user_query = user_query[:1]
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
