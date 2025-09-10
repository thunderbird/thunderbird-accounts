import zoneinfo

import sentry_sdk
from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import (
    InvalidDomainError,
    UpdateUserError,
    SendExecuteActionsEmailError,
)
from thunderbird_accounts.authentication.models import User


class CustomUserFormBase(forms.ModelForm):
    """Base class to use for custom user admin forms, contains some field overrides and cleaning functions."""

    class Meta:
        model = User
        fields = '__all__'

    username = forms.CharField(
        label=_('Thundermail Address'),
        required=True,
        strip=False,
        widget=forms.EmailInput(),
        help_text=_(
            f'This is the primary thundermail address. Please end with '
            f'{settings.ALLOWED_EMAIL_DOMAINS[0] if settings.ALLOWED_EMAIL_DOMAINS else "example.org"}. '
            f'This must be unique!'
        ),
    )
    email = forms.CharField(
        label=_('Recovery Email Address'),
        required=True,
        strip=False,
        widget=forms.EmailInput(),
        help_text=_(
            "This is the recovery email address. This should not be a thundermail address, but I can't stop you."
        ),
    )
    timezone = forms.CharField(
        label=_('Timezone'),
        required=True,
        strip=False,
        widget=forms.TextInput(),
        help_text=_(
            'The user\'s timezone. Should be in <a href="{url}">tz format</a>.'.format(
                url='https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List')
        ),
    )

    def clean(self):
        if not self.data.get('email'):
            self.add_error('email', _('A recovery email is required.'))

        if not self.data.get('timezone'):
            self.add_error('timezone', _('A timezone (e.g. America/Vancouver or UTC) is required.'))
        else:
            try:
                zoneinfo.ZoneInfo(self.data.get('timezone'))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError) as ex:
                self.add_error('timezone', str(ex))

        return super().clean()

    def _post_clean(self):
        super()._post_clean()


class CustomNewUserForm(CustomUserFormBase):
    def save(self, commit=True):
        user = super().save(commit=False)

        # Create the user on keycloak's end
        keycloak = KeycloakClient()
        try:
            keycloak_pkid = keycloak.import_user(
                user.username, user.email, user.timezone, name=None, send_reset_password_email=True
            )

            # Save the oidc id so it matches on login
            user.oidc_id = keycloak_pkid
        except SendExecuteActionsEmailError as ex:
            sentry_sdk.capture_exception(ex)
            # Don't think this will show
            self.add_error(None, _('Failed to send update password email.'))

        # Let ImportError raise since we cannot handle error messages here
        # TODO: Fix that...

        # Actually save the user
        if commit:
            user.save()

        return user


class CustomUserChangeForm(CustomUserFormBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user_permissions = self.fields.get('user_permissions')
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related('content_type')

    def save(self, commit=True):
        user = super().save(commit=False)
        updated_keycloak_successfully = False

        # Update the user on keycloak's end
        keycloak = KeycloakClient()
        try:
            keycloak.update_user(
                user.oidc_id,
                username=user.username,
                email=user.email,
                enabled=user.is_active,
                timezone=user.timezone,
                locale=user.language,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            updated_keycloak_successfully = True
        except (ValueError, InvalidDomainError) as ex:
            self.add_error('username', str(ex))
        except UpdateUserError as ex:
            sentry_sdk.capture_exception(ex)
            self.add_error(None, _(f'There was an error updating in keycloak. Technical Error: {ex}'))

        if not updated_keycloak_successfully:
            raise ValueError('Keycloak was not updated successfully!')

        # Actually save the user
        if commit:
            user.save()

        return user
