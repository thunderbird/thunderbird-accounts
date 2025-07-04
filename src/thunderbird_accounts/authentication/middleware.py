import logging
import time

import sentry_sdk
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from socket import gethostbyname, gethostname


from .models import User
from .utils import is_email_in_allow_list
from ..client.models import ClientEnvironment

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
        user.timezone = claims.get('zoneinfo')
        user.avatar_url = claims.get('picture')
        user.display_name = claims.get('preferred_username')
        user.username = claims.get('preferred_username')

        # Non-standard
        user.is_staff = claims.get('is_services_admin', 'no').lower() == 'yes'

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
        return self.UserModel.objects.filter(oidc_id__iexact=sub)


class FXABackend(BaseBackend):
    def authenticate(self, request, fxa_id=None, email=None):
        user_model = get_user_model()

        # First look-up by fxa id
        try:
            user = user_model.objects.get(fxa_id=fxa_id)
            if user.email != email:
                user.last_used_email = user.email
                user.email = email
                user.save()
        except user_model.DoesNotExist:
            user = None

        # If that doesn't work, look up by email
        if user is None:
            try:
                user = user_model.objects.get(email=email)
                user.fxa_id = fxa_id
                user.save()

            except user_model.DoesNotExist:
                user = None

        return user

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None


class ClientSetAllowedHostsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        start = time.perf_counter_ns()

        allowed_hosts = cache.get(settings.ALLOWED_HOSTS_CACHE_KEY)
        allowed_origins = cache.get(settings.ALLOWED_ORIGINS_CACHE_KEY)
        if not allowed_hosts or not allowed_origins:
            allowed_hosts, allowed_origins = ClientEnvironment.cache_hostnames()
        # Get the IP of whatever machine is running this code and allow it as a hostname
        allowed_hosts.append(gethostbyname(gethostname()))

        # Set both django allowed hosts and cors allowed origins
        settings.ALLOWED_HOSTS = allowed_hosts
        settings.CORS_ALLOWED_ORIGINS = allowed_origins

        end = time.perf_counter_ns()

        sentry_sdk.set_extra('cached_allowed_host_get_time_ms', (end - start) / 1000000)

        response = self.get_response(request)

        return response
