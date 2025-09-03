import logging

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _, ngettext
from thunderbird_accounts.mail import utils as mail_utils
from .models import User
from ..mail.client import MailClient
from ..mail.exceptions import AccountNotFoundError


@admin.action(description="Fix Broken Stalwart Account")
def admin_create_stalwart_account(modeladmin, request, queryset):
    success_new_account = 0
    success_fixed_missing_email = 0
    errors = 0

    for user in queryset:
        account_not_found = user.account_set.length == 0

        if user.account_set.length == 0:
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


class CustomUserAdmin(UserAdmin):
    list_display = ('uuid', *UserAdmin.list_display, 'oidc_id', 'last_used_email', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('uuid',)}),
        *UserAdmin.fieldsets,
        (_('Profile Info'), {'fields': ('display_name', 'avatar_url', 'timezone')}),
        (
            _('External Account info'),
            {'fields': ('oidc_id',)},
        ),
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


admin.site.register(User, CustomUserAdmin)
