from thunderbird_accounts.subscription.tasks import add_subscriber_to_mailchimp_list
import logging

from django.conf import settings
from django.contrib import messages, admin
from django.utils.translation import gettext_lazy as _, ngettext

from thunderbird_accounts.authentication.exceptions import UpdateUserPlanInfoError
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail import utils as mail_utils
from thunderbird_accounts.mail.exceptions import AccountNotFoundError
from thunderbird_accounts.subscription.utils import sync_plan_to_keycloak, activate_subscription_features


@admin.action(description=_('Fix Broken Stalwart Account'))
def admin_fix_broken_stalwart_account(modeladmin, request, queryset):
    """Run through some common edge-cases to hopefully repair a broken relationship to a stalwart account"""
    success_new_account = 0
    success_fixed_missing_email = 0
    errors = 0

    stalwart = MailClient()

    for user in queryset:
        account_not_found = user.account_set.count() == 0

        if account_not_found:
            # We don't have a record of the Stalwart account associated with this user.
            # So we need to check if Stalwart has anything on their end
            try:
                account = stalwart.get_account(user.stalwart_primary_email)

                missing_emails = []
                primary_email_address = user.stalwart_primary_email
                for _domain in settings.ALLOWED_EMAIL_DOMAINS:
                    # This will also check primary_email_address so we don't skip it
                    email_to_check = primary_email_address.replace(f'@{settings.PRIMARY_EMAIL_DOMAIN}', f'@{_domain}')
                    if email_to_check not in account.get('emails', []):
                        missing_emails.append(email_to_check)

                if len(missing_emails) > 0:
                    # They have an account, but don't have an email address associated with their account.
                    # Fix that!
                    mail_utils.add_email_addresses_to_stalwart_account(user, missing_emails)
                    success_fixed_missing_email += 1

            except AccountNotFoundError:
                account_not_found = True
            except Exception as ex:
                logging.error(f'[admin_create_stalwart_account] Problem fixing stalwart email address {ex}')
                errors += 1
        else:
            try:
                # They have an Account+Email on accounts, but do they have data on Stalwart?
                stalwart.get_account(user.stalwart_primary_email)
            except AccountNotFoundError:
                # Okay fall-through to make the account
                account_not_found = True

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


@admin.action(description=_('Manually activate subscription features'))
def admin_manual_activate_subscription_features(modeladmin, request, queryset):
    success_activate = 0
    errors = 0

    for user in queryset:
        try:
            activate_subscription_features(user, user.plan)
            success_activate += 1
        except UpdateUserPlanInfoError as ex:
            logging.error(ex)
            errors += 1

    if success_activate:
        modeladmin.message_user(
            request,
            ngettext(
                'Activated %d plan.',
                'Activated %d plans.',
                success_activate,
            )
            % success_activate,
            messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            ngettext(
                'Failed to update %d plan.',
                'Failed to update %d plans.',
                errors,
            )
            % errors,
            messages.ERROR,
        )
    if sum([success_activate, errors]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to update!'),
            messages.INFO,
        )


@admin.action(description=_('Sync plan information to Keycloak'))
def admin_sync_plan_to_keycloak(modeladmin, request, queryset):
    success_activate = 0
    success_deactivate = 0
    errors = 0

    for user in queryset:
        try:
            sync_plan_to_keycloak(user)
        except UpdateUserPlanInfoError as ex:
            logging.error(ex)
            errors += 1
            continue

        if not user.has_active_subscription:
            success_deactivate += 1
        else:
            success_activate += 1

    if success_activate:
        modeladmin.message_user(
            request,
            ngettext(
                'Synced %d plan with an active subscription.',
                'Synced %d plans with active subscriptions.',
                success_activate,
            )
            % success_activate,
            messages.SUCCESS,
        )
    if success_deactivate:
        modeladmin.message_user(
            request,
            ngettext(
                'Synced %d plan with an inactive subscription.',
                'Synced %d plans with inactive subscriptions.',
                success_deactivate,
            )
            % success_deactivate,
            messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            ngettext(
                'Failed to update %d plan.',
                'Failed to update %d plans.',
                errors,
            )
            % errors,
            messages.ERROR,
        )
    if sum([success_activate, success_deactivate, errors]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to update!'),
            messages.INFO,
        )


@admin.action(description=_('Add to Mailchimp list'))
def admin_add_to_mailchimp_list(modeladmin, request, queryset):
    if not settings.USE_MAILCHIMP:
        modeladmin.message_user(
            request,
            _('Mailchimp support is disabled.'),
            messages.WARNING,
        )
        return

    success = 0
    errors = 0
    error_titles = {}

    for user in queryset:
        results = add_subscriber_to_mailchimp_list.run(str(user.uuid))
        if results.get('task_status') == 'failed':
            errors += 1
            if results.get('error_msg_title'):
                error_titles[results.get('error_msg_title')] = True
        else:
            success += 1

    if success:
        modeladmin.message_user(
            request,
            ngettext(
                'Added %d user to the Mailchimp list.',
                'Added %d users to the Mailchimp list.',
                success,
            )
            % success,
            messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            ngettext(
                'Failed to add %d user to the Mailchimp list.',
                'Failed to add %d users to the Mailchimp list.',
                errors,
            )
            % errors,
            messages.ERROR,
        )
        if len(error_titles) > 0:
            modeladmin.message_user(
                request,
                _(f'Encountered the following errors: {', '.join(error_titles.keys())}'),
                messages.ERROR,
            )
    if sum([success, errors]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to do!'),
            messages.INFO,
        )
