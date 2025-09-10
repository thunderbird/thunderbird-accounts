import logging

from django.conf import settings
from django.contrib import messages, admin
from django.utils.translation import gettext_lazy as _, ngettext

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail import utils as mail_utils
from thunderbird_accounts.mail.exceptions import AccountNotFoundError


@admin.action(description=_('Fix Broken Stalwart Account'))
def admin_create_stalwart_account(modeladmin, request, queryset):
    """Run through some common edge-cases to hopefully repair a broken relationship to a stalwart account"""
    success_new_account = 0
    success_fixed_missing_email = 0
    errors = 0

    for user in queryset:
        account_not_found = user.account_set.count() == 0

        if account_not_found:
            # We don't have a record of the Stalwart account associated with this user.
            # So we need to check if Stalwart has anything on their end
            stalwart = MailClient()
            try:
                account = stalwart.get_account(user.oidc_id)
                if user.stalwart_primary_email not in account.get('emails', []):
                    # They have an account, but don't have an email address associated with their account.
                    # Fix that!
                    mail_utils.add_email_address_to_stalwart_account(user, user.stalwart_primary_email)
                    success_fixed_missing_email += 1

            except AccountNotFoundError:
                account_not_found = True
            except Exception as ex:
                logging.error(f'[admin_create_stalwart_account] Problem fixing stalwart email address {ex}')
                errors += 1

        # Allows us to fall-through from the previous if branch
        if account_not_found and any([user.username.endswith(domain) for domain in settings.ALLOWED_EMAIL_DOMAINS]):
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
                'Created %d Stalwart account.',
                'Created %d Stalwart accounts.',
                success_new_account,
            )
            % success_new_account,
            messages.SUCCESS,
        )
    if success_fixed_missing_email:
        modeladmin.message_user(
            request,
            ngettext(
                'Fixed %d Stalwart email address.',
                'Fixed %d Stalwart email addresses.',
                success_fixed_missing_email,
            )
            % success_fixed_missing_email,
            messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            ngettext(
                'Failed to fix %d Stalwart account.',
                'Failed to fix %d Stalwart accounts.',
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
