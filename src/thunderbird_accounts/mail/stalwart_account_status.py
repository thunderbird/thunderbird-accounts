"""Stalwart side of user access: the account's ``authenticate`` permission mirrors ``UserAccess.has_services``."""

from thunderbird_accounts.authentication.account_status import AccountStatusHandler, UserAccess
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient


class StalwartAccountStatusHandler(AccountStatusHandler):
    label = 'Stalwart'

    def sync(self, user: User, access: UserAccess) -> None:
        primary_email = user.stalwart_primary_email
        if not primary_email:
            return

        MailClient().set_account_active(primary_email, access.has_services)
        # Local mirror of the Stalwart state, written only once Stalwart accepted the change.
        user.account_set.update(active=access.has_services)
