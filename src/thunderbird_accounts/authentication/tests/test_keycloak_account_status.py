from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase

from thunderbird_accounts.authentication.account_status import UserAccess
from thunderbird_accounts.authentication.exceptions import KeycloakError, LogoutUserError, UpdateUserError
from thunderbird_accounts.authentication.keycloak_account_status import KeycloakAccountStatusHandler
from thunderbird_accounts.authentication.models import User

OIDC_ID = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'
SIGN_IN = UserAccess(can_sign_in=True, has_services=True)
LOCKED = UserAccess(can_sign_in=False, has_services=False)


@patch('thunderbird_accounts.authentication.keycloak_account_status.KeycloakClient')
class KeycloakAccountStatusHandlerTestCase(TestCase):
    def setUp(self):
        self.username = f'person@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.user = User.objects.create(username=self.username, oidc_id=OIDC_ID, email='recovery@example.com')
        self.handler = KeycloakAccountStatusHandler()

    def test_user_without_oidc_id_is_skipped(self, mock_keycloak_cls: MagicMock):
        self.user.oidc_id = None

        self.handler.sync(self.user, LOCKED)

        mock_keycloak_cls.assert_not_called()

    def test_sign_in_enables_without_a_logout(self, mock_keycloak_cls: MagicMock):
        self.handler.sync(self.user, SIGN_IN)

        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.assert_called_once_with(OIDC_ID, enabled=True)
        keycloak.logout_user.assert_not_called()

    def test_locked_disables_and_logs_out(self, mock_keycloak_cls: MagicMock):
        self.handler.sync(self.user, LOCKED)

        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.assert_called_once_with(OIDC_ID, enabled=False)
        keycloak.logout_user.assert_called_once_with(OIDC_ID)

    def test_disable_failure_still_logs_out_then_raises_it(self, mock_keycloak_cls: MagicMock):
        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.side_effect = UpdateUserError(error='boom', username=self.username)

        with self.assertRaises(UpdateUserError):
            self.handler.sync(self.user, LOCKED)

        keycloak.logout_user.assert_called_once_with(OIDC_ID)

    def test_logout_failure_alone_is_raised_unchanged(self, mock_keycloak_cls: MagicMock):
        keycloak = mock_keycloak_cls.return_value
        keycloak.logout_user.side_effect = LogoutUserError(oidc_id=OIDC_ID, error='bang')

        with self.assertRaises(LogoutUserError):
            self.handler.sync(self.user, LOCKED)

    def test_both_failures_are_combined_into_one_error(self, mock_keycloak_cls: MagicMock):
        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.side_effect = UpdateUserError(error='boom', username=self.username)
        keycloak.logout_user.side_effect = LogoutUserError(oidc_id=OIDC_ID, error='bang')

        with self.assertRaises(KeycloakError) as raised:
            self.handler.sync(self.user, LOCKED)

        self.assertIn('boom', str(raised.exception))
        self.assertIn('bang', str(raised.exception))
