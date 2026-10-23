from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase

from thunderbird_accounts.authentication.account_status import set_user_active
from thunderbird_accounts.authentication.exceptions import UpdateUserError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.exceptions import AccountNotFoundError
from thunderbird_accounts.mail.models import Account, Email

OIDC_ID = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'


@patch('thunderbird_accounts.authentication.account_status.MailClient')
@patch('thunderbird_accounts.authentication.account_status.KeycloakClient')
class SetUserActiveTestCase(TestCase):
    def setUp(self):
        self.username = f'person@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.user = User.objects.create(username=self.username, oidc_id=OIDC_ID, email='recovery@example.com')
        self.account = Account.objects.create(name=self.username, user=self.user)
        Email.objects.create(address=self.username, type=Email.EmailType.PRIMARY, account=self.account)

    def test_deactivation_is_mirrored_to_keycloak_and_stalwart(self, mock_keycloak_cls: MagicMock, mock_mail_cls):
        errors = set_user_active(self.user, False)

        self.assertEqual(errors, [])
        self.user.refresh_from_db()
        self.account.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.deactivated_at)
        self.assertFalse(self.account.active)

        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.assert_called_once_with(OIDC_ID, enabled=False)
        keycloak.logout_user.assert_called_once_with(OIDC_ID)
        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, False)

    def test_reactivation_restores_everything_without_a_logout(self, mock_keycloak_cls: MagicMock, mock_mail_cls):
        set_user_active(self.user, False)
        mock_keycloak_cls.reset_mock()
        mock_mail_cls.reset_mock()

        errors = set_user_active(self.user, True)

        self.assertEqual(errors, [])
        self.user.refresh_from_db()
        self.account.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.deactivated_at)
        self.assertTrue(self.account.active)

        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.assert_called_once_with(OIDC_ID, enabled=True)
        keycloak.logout_user.assert_not_called()
        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, True)

    def test_keycloak_failure_is_reported_and_stalwart_still_updated(self, mock_keycloak_cls: MagicMock, mock_mail_cls):
        mock_keycloak_cls.return_value.update_user.side_effect = UpdateUserError(error='boom', username=self.username)

        errors = set_user_active(self.user, False)

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('Keycloak:'), errors)
        mock_keycloak_cls.return_value.logout_user.assert_not_called()
        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_stalwart_failure_is_reported_and_local_account_flag_is_left_alone(
        self, mock_keycloak_cls: MagicMock, mock_mail_cls
    ):
        mock_mail_cls.return_value.set_account_active.side_effect = AccountNotFoundError(self.username)

        errors = set_user_active(self.user, False)

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('Stalwart:'), errors)
        self.account.refresh_from_db()
        self.assertTrue(self.account.active)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_user_without_keycloak_or_stalwart_links_only_changes_locally(
        self, mock_keycloak_cls: MagicMock, mock_mail_cls
    ):
        user = User.objects.create(username=f'unlinked@{settings.PRIMARY_EMAIL_DOMAIN}', email='u@example.com')

        errors = set_user_active(user, False)

        self.assertEqual(errors, [])
        mock_keycloak_cls.assert_not_called()
        mock_mail_cls.assert_not_called()
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deactivated_at)
