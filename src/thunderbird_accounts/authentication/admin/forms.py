import zoneinfo
from typing import Optional

import sentry_sdk
from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import (
    InvalidDomainError,
    UpdateUserError,
    SendExecuteActionsEmailError,
    ImportUserError,
)
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient


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
                url='https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List'
            )
        ),
    )
    oidc_id = forms.CharField(
        label=_('Keycloak User ID'),
        required=False,
        strip=False,
        widget=forms.TextInput(),
        help_text=_("The user's Keycloak ID field. <b>Don't change this unless you know what you're doing!</b>"),
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
    oidc_id: Optional[str] = None

    def clean(self):
        super().clean()

        # Don't continue with clean
        if len(self.errors) > 0:
            return

        # Create the user on keycloak's end
        keycloak = KeycloakClient()
        try:
            name = f'{self.cleaned_data.get("first_name", "")} {self.cleaned_data.get("last_name", "")}'.strip()
            keycloak_pkid = keycloak.import_user(
                self.cleaned_data.get('username'),
                self.cleaned_data.get('email'),
                self.cleaned_data.get('timezone'),
                name=name,
                send_reset_password_email=True,
            )

            # Save the oidc id so it matches on login
            self.oidc_id = keycloak_pkid
        except (ValueError, InvalidDomainError) as ex:
            # Only username errors raise ValueErrors right now
            self.add_error('username', str(ex))
        except ImportUserError as ex:
            sentry_sdk.capture_exception(ex)
            self.add_error(None, _(f'Could not create user in Keycloak. Tell a developer: {ex}'))
        except SendExecuteActionsEmailError as ex:
            sentry_sdk.capture_exception(ex)
            # We don't have a way to add a warning, and we don't want this error preventing user creation!
            # self.add_error(None, _(f'User created in Keycloak but could not send them an email to add their password.
            # Tell a developer: {ex}'))

    def save(self, commit=True):
        user = super().save(commit=False)

        user.oidc_id = self.oidc_id

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

    def clean(self):
        super().clean()

        # Don't continue with clean
        if len(self.errors) > 0:
            return

        username = self.cleaned_data.get('username')
        full_name = f'{self.cleaned_data.get("first_name")} {self.cleaned_data.get("last_name")}'.strip()

        # Update the user on keycloak's end
        keycloak = KeycloakClient()
        try:
            keycloak.update_user(
                self.cleaned_data.get('oidc_id'),
                username=username,
                email=self.cleaned_data.get('email'),
                enabled=self.cleaned_data.get('is_active'),
                timezone=self.cleaned_data.get('timezone'),
                locale=self.cleaned_data.get('language'),
                first_name=self.cleaned_data.get('first_name'),
                last_name=self.cleaned_data.get('last_name'),
            )
        except (ValueError, InvalidDomainError) as ex:
            self.add_error('username', str(ex))
        except UpdateUserError as ex:
            sentry_sdk.capture_exception(ex)
            self.add_error(None, _(f'There was an error updating in keycloak. Tell a developer: {ex}'))

        stalwart = MailClient()
        try:
            # We can only send stalwart updates if they actually have an account reference
            account = self.instance.account_set.first()
            if account:
                old_full_name = f'{self.initial.get("first_name")} {self.initial.get("last_name")}'.strip()
                old_username = self.initial.get('username')

                new_primary_email_address = None
                new_full_name = None

                if old_username != username:
                    new_primary_email_address = username

                if old_full_name != full_name:
                    new_full_name = full_name

                if new_primary_email_address or new_full_name:
                    stalwart.update_individual(
                        old_username, primary_email_address=new_primary_email_address, full_name=new_full_name
                    )

        except (User.DoesNotExist, ValueError, RuntimeError) as ex:
            sentry_sdk.capture_exception(ex)
            self.add_error(None, _(f'There was an error updating in stalwart. Tell a developer: {ex}'))

    def save(self, commit=True):
        user: User = super().save(commit=False)

        # Actually save the user
        if commit:
            user.save()

        return user
