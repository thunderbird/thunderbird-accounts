import datetime

from django.contrib import messages, admin
from django.utils.translation import gettext_lazy as _, ngettext

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.models import Account


@admin.action(description=_('Fix Empty Stalwart IDs (#323)'))
def admin_fix_stalwart_ids(modeladmin, request, queryset):
    """Queries stalwart accounts and fixes any empty Stalwart IDs as well as fill in any empty timestamps."""
    success = 0

    stalwart = MailClient()
    for account in queryset:
        account: Account
        if account.stalwart_id is not None:
            continue

        stalwart_account = stalwart.get_account(account.name)

        now = datetime.datetime.now(datetime.UTC)
        account.stalwart_id = stalwart_account.get('id')
        if not account.stalwart_created_at:
            account.stalwart_created_at = now
        if not account.stalwart_updated_at or account.stalwart_updated_at < now:
            account.stalwart_updated_at = now
        account.save()
        success += 1

    if success:
        modeladmin.message_user(
            request,
            ngettext(
                'Matched %d Stalwart account with their id.',
                'Matched %d Stalwart accounts with their ids.',
                success,
            )
            % success,
            messages.SUCCESS,
        )
    if sum([success]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to fix!'),
            messages.INFO,
        )
