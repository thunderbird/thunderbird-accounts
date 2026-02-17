from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError
import datetime

from django.contrib import messages, admin
from django.utils.translation import gettext_lazy as _, ngettext

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.models import Account, BaseStalwartObject, Domain


@admin.action(description=_('Fix Empty Stalwart IDs (#323)'))
def admin_fix_stalwart_ids(modeladmin, request, queryset):
    """Queries stalwart base objects and fixes any empty Stalwart IDs as well as fill in any empty timestamps."""
    success = 0
    ignored = 0
    not_found = 0

    stalwart = MailClient()
    results = queryset.filter(stalwart_id__isnull=True)

    for principal_obj in results:
        principal_obj: BaseStalwartObject

        try:
            # These are duplicated like so, but .name is not on the base object
            # and responses may vary.
            if isinstance(principal_obj, Account):
                data = stalwart.get_account(principal_obj.name)
                stalwart_id = data.get('id')
            elif isinstance(principal_obj, Domain):
                data = stalwart.get_domain(principal_obj.name)
                stalwart_id = data.get('id')
            else:
                ignored += 1
                continue
        except (AccountNotFoundError, DomainNotFoundError):
            not_found += 1
            continue

        now = datetime.datetime.now(datetime.UTC)
        principal_obj.stalwart_id = stalwart_id
        if not principal_obj.stalwart_created_at:
            principal_obj.stalwart_created_at = now
        if not principal_obj.stalwart_updated_at or principal_obj.stalwart_updated_at < now:
            principal_obj.stalwart_updated_at = now
        principal_obj.save()
        success += 1

    if success:
        modeladmin.message_user(
            request,
            ngettext(
                'Matched %d Stalwart objects with their id.',
                'Matched %d Stalwart objects with their ids.',
                success,
            )
            % success,
            messages.SUCCESS,
        )
    if ignored:
        modeladmin.message_user(
            request,
            ngettext(
                'Ignored %d principal object as they were not an Account or Domain.',
                'Ignored %d principal objects as they were not an Account or Domain.',
                ignored,
            )
            % ignored,
            messages.INFO,
        )
    if not_found:
        modeladmin.message_user(
            request,
            ngettext(
                'Could not find %d principal object within Stalwart.',
                'Could not find %d principal objects within Stalwart.',
                not_found,
            )
            % not_found,
            messages.ERROR,
        )
    if sum([success, ignored, not_found]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to fix!'),
            messages.INFO,
        )
