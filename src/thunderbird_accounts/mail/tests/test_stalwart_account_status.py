from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase

from thunderbird_accounts.authentication.account_status import UserAccess
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.exceptions import AccountNotFoundError
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.mail.stalwart_account_status import StalwartAccountStatusHandler

WITH_SERVICES = UserAccess(can_sign_in=True, has_services=True)
WITHOUT_SERVICES = UserAccess(can_sign_in=True, has_services=False)


@patch('thunderbird_accounts.mail.stalwart_account_status.MailClient')
class StalwartAccountStatusHandlerTestCase(TestCase):
    def setUp(self):
        self.username = f'person@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.user = User.objects.create(username=self.username, email='recovery@example.com')
        self.account = Account.objects.create(name=self.username, user=self.user)
        self.handler = StalwartAccountStatusHandler()

    def _add_primary_email(self):
        Email.objects.create(address=self.username, type=Email.EmailType.PRIMARY, account=self.account)

    def test_user_without_a_primary_email_is_skipped(self, mock_mail_cls: MagicMock):
        self.handler.sync(self.user, WITHOUT_SERVICES)

        mock_mail_cls.assert_not_called()
        self.account.refresh_from_db()
        self.assertTrue(self.account.active)

    def test_losing_services_locks_the_account_and_mirrors_it_locally(self, mock_mail_cls: MagicMock):
        self._add_primary_email()

        self.handler.sync(self.user, WITHOUT_SERVICES)

        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, False)
        self.account.refresh_from_db()
        self.assertFalse(self.account.active)

    def test_regaining_services_unlocks_the_account(self, mock_mail_cls: MagicMock):
        self._add_primary_email()
        Account.objects.filter(pk=self.account.pk).update(active=False)

        self.handler.sync(self.user, WITH_SERVICES)

        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, True)
        self.account.refresh_from_db()
        self.assertTrue(self.account.active)

    def test_stalwart_failure_propagates_and_leaves_the_local_flag_alone(self, mock_mail_cls: MagicMock):
        self._add_primary_email()
        mock_mail_cls.return_value.set_account_active.side_effect = AccountNotFoundError(self.username)

        with self.assertRaises(AccountNotFoundError):
            self.handler.sync(self.user, WITHOUT_SERVICES)

        self.account.refresh_from_db()
        self.assertTrue(self.account.active)
