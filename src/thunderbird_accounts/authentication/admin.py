import datetime
import logging
import zoneinfo

import sentry_sdk
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _, ngettext
from thunderbird_accounts.mail import utils as mail_utils
from .clients import KeycloakClient
from .exceptions import InvalidDomainError, UpdateUserError
from .models import User
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.exceptions import AccountNotFoundError


@admin.action(description="Fix Broken Stalwart Account")
def admin_create_stalwart_account(modeladmin, request, queryset):
    success_new_account = 0
    success_fixed_missing_email = 0
    errors = 0

    for user in queryset:
        account_not_found = user.account_set.length == 0

        if account_not_found:
            # Yes relationship, let's check stalwart's side
            stalwart = MailClient()
            try:
                account = stalwart.get_account(user.oidc_id)
                if user.stalwart_primary_email not in account.get('emails', []):
                    mail_utils.add_email_address_to_stalwart_account(user, user.stalwart_primary_email)
                    success_fixed_missing_email += 1

            except AccountNotFoundError:
                account_not_found = True
            except Exception as ex:
                logging.error(f'[admin_create_stalwart_account] Problem fixing stalwart email address {ex}')
                errors += 1

        # Allows us to fall-through from the previous if branch
        if account_not_found and any(
                [user.username.endswith(domain) for domain in settings.ALLOWED_EMAIL_DOMAINS]):
            # No Accounts/Email model relationship
            try:
                mail_utils.create_stalwart_account(user)
                success_new_account += 1
            except Exception as ex:
                logging.error(f'[admin_create_stalwart_account] Problem creating stalwart account {ex}')
                errors += 1

    if success_new_account:
        modeladmin.message_user(
            request,
            ngettext(
                "Created %d Stalwart account.",
                "Created %d Stalwart accounts.",
                success_new_account,
            )
            % success_new_account,
            messages.SUCCESS,
        )
    if success_fixed_missing_email:
        modeladmin.message_user(
            request,
            ngettext(
                "Fixed %d Stalwart email address.",
                "Fixed %d Stalwart email addresses.",
                success_fixed_missing_email,
            )
            % success_fixed_missing_email,
            messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            ngettext(
                "Failed to fix %d Stalwart account.",
                "Failed to fix %d Stalwart accounts.",
                errors,
            )
            % errors,
            messages.ERROR,
        )
    if sum([success_fixed_missing_email, success_new_account, errors]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to fix!'),
            messages.INFO,
        )


class CustomUserFormBase(forms.ModelForm):
    """Base class to use for custom user admin forms, contains some field overrides and cleaning functions."""
    class Meta:
        model = User
        fields = "__all__"

    username = forms.CharField(
        label='Thundermail Address',
        required=True,
        strip=False,
        widget=forms.EmailInput(),
        help_text=f'This is the primary thundermail address. Please end with {'@stage-thundermail.com' if settings.APP_ENV == 'stage' else '@thundermail.com'}. This must be unique!',
    )
    email = forms.CharField(
        label='Recovery Email Address',
        required=True,
        strip=False,
        widget=forms.EmailInput(),
        help_text='This is the recovery email address. This should not be a thundermail address, but I can\'t stop you.',
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
        keycloak_pkid = keycloak.import_user(user.username, user.email, user.timezone, name=None,
                                             send_reset_password_email=True)

        # Save the oidc id so it matches on login
        user.oidc_id = keycloak_pkid

        # Actually save the user
        user.save()

        return user


class CustomUserChangeForm(CustomUserFormBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user_permissions = self.fields.get("user_permissions")
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related(
                "content_type"
            )

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


class CustomUserAdmin(UserAdmin):
    list_display = ('uuid', 'oidc_id', *UserAdmin.list_display, 'last_used_email', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('uuid', 'username')}),
        (
            _('Keycloak Account info'),
            {'fields': ('oidc_id',)},
        ),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (_('Profile Info'), {'fields': ('display_name', 'avatar_url', 'timezone')}),

        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = UserAdmin.readonly_fields + (
        'uuid',
        'display_name',
        'avatar_url',
        'oidc_id',
        'created_at',
        'updated_at',
    )
    actions = [admin_create_stalwart_account]

    form = CustomUserChangeForm
    add_form = CustomNewUserForm

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "timezone"),
            },
        ),
    )

    def delete_queryset(self, request, queryset):
        """Given a queryset, delete it from the database."""
        for model in queryset:
            self.delete_model(request, model)

    def delete_model(self, request, obj: User):
        if obj.oidc_id:
            # Create the user on keycloak's end
            keycloak = KeycloakClient()
            keycloak.delete_user(obj.oidc_id)

            # Delete the stalwart email too!
            if obj.stalwart_primary_email:
                stalwart = MailClient()
                stalwart.delete_account(obj.oidc_id)
        # Finally delete the rest of the model
        super().delete_model(request, obj)



admin.site.register(User, CustomUserAdmin)
