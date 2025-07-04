import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied


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
