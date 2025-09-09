import zoneinfo

import sentry_sdk
from django import forms
from django.conf import settings
from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import InvalidDomainError, UpdateUserError
from thunderbird_accounts.authentication.models import User


class CustomUserFormBase(forms.ModelForm):
    """Base class to use for custom user admin forms, contains some field overrides and cleaning functions."""

    class Meta:
        model = User
        fields = '__all__'

    username = forms.CharField(
        label='Thundermail Address',
        required=True,
        strip=False,
        widget=forms.EmailInput(),
        help_text=(f'This is the primary thundermail address. Please end with '
                   f'{settings.ALLOWED_EMAIL_DOMAINS[0] if settings.ALLOWED_EMAIL_DOMAINS else 'example.org'}. '
                   f'This must be unique!'),
    )
    email = forms.CharField(
        label='Recovery Email Address',
        required=True,
        strip=False,
        widget=forms.EmailInput(),
        help_text="This is the recovery email address. This should not be a thundermail address, but I can't stop you.",
    )

    def clean(self):
        if not self.data.get('email'):
            self.add_error('email', 'A recovery email is required.')

        if not self.data.get('timezone'):
            self.add_error('timezone', 'A timezone (e.g. America/Vancouver or UTC) is required.')
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
        keycloak_pkid = keycloak.import_user(
            user.username, user.email, user.timezone, name=None, send_reset_password_email=True
        )

        # Save the oidc id so it matches on login
        user.oidc_id = keycloak_pkid

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

        # Create the user on keycloak's end
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
            self.add_error(None, f'There was an error updating in keycloak. Technical Error: {ex}')

        if not updated_keycloak_successfully:
            raise ValueError('Keycloak was not updated successfully!')

        # Actually save the user
        user.save()

        return user
