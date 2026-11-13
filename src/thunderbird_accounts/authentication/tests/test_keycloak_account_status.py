from unittest.mock import ANY, MagicMock, patch

from django.conf import settings
from django.test import TestCase

from thunderbird_accounts.authentication.account_status import UserAccess
from thunderbird_accounts.authentication.exceptions import (
    GetUserError,
    KeycloakError,
    LogoutUserError,
    UpdateUserError,
)
from thunderbird_accounts.authentication.keycloak_account_status import KeycloakAccountStatusHandler
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.core.tests.utils import build_keycloak_success_response

OIDC_ID = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'
FULL_ACCESS = UserAccess(can_sign_in=True, has_services=True)
SIGN_IN_ONLY = UserAccess(can_sign_in=True, has_services=False)
LOCKED = UserAccess(can_sign_in=False, has_services=False)


def _keycloak_user(enabled: bool, is_subscribed: str | None) -> dict:
    attributes = {'zoneinfo': ['UTC']}
    if is_subscribed is not None:
        attributes['is_subscribed'] = [is_subscribed]
    return {'id': OIDC_ID, 'enabled': enabled, 'attributes': attributes}


@patch('thunderbird_accounts.authentication.keycloak_account_status.KeycloakClient')
class KeycloakAccountStatusHandlerTestCase(TestCase):
    def setUp(self):
        self.username = f'person@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.user = User.objects.create(username=self.username, oidc_id=OIDC_ID, email='recovery@example.com')
        self.handler = KeycloakAccountStatusHandler()

    def _given_keycloak_user(self, mock_keycloak_cls: MagicMock, enabled: bool, is_subscribed: str | None) -> dict:
        current = _keycloak_user(enabled, is_subscribed)
        mock_keycloak_cls.return_value.get_user.return_value = build_keycloak_success_response(current)
        return current

    def test_user_without_oidc_id_is_skipped(self, mock_keycloak_cls: MagicMock):
        self.user.oidc_id = None

        self.handler.sync(self.user, LOCKED)

        mock_keycloak_cls.assert_not_called()

    def test_full_access_writes_enabled_and_subscribed_in_one_update(self, mock_keycloak_cls: MagicMock):
        current = self._given_keycloak_user(mock_keycloak_cls, enabled=False, is_subscribed='false')

        self.handler.sync(self.user, FULL_ACCESS)

        keycloak = mock_keycloak_cls.return_value
        keycloak.get_user.assert_called_once_with(OIDC_ID)
        keycloak.update_user.assert_called_once_with(
            OIDC_ID, enabled=True, attributes={'is_active': 'true', 'is_subscribed': 'true'}, user_data=current
        )
        keycloak.logout_user.assert_not_called()

    def test_losing_the_subscription_writes_false_and_logs_out(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='true')

        self.handler.sync(self.user, SIGN_IN_ONLY)

        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.assert_called_once_with(
            OIDC_ID, enabled=True, attributes={'is_active': 'true', 'is_subscribed': 'false'}, user_data=ANY
        )
        keycloak.logout_user.assert_called_once_with(OIDC_ID)

    def test_legacy_yes_counts_as_subscribed(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='yes')

        self.handler.sync(self.user, SIGN_IN_ONLY)

        mock_keycloak_cls.return_value.logout_user.assert_called_once_with(OIDC_ID)

    def test_locked_disables_and_logs_out(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='true')

        self.handler.sync(self.user, LOCKED)

        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.assert_called_once_with(
            OIDC_ID, enabled=False, attributes={'is_active': 'false', 'is_subscribed': 'false'}, user_data=ANY
        )
        keycloak.logout_user.assert_called_once_with(OIDC_ID)

    def test_unchanged_state_does_not_log_out(self, mock_keycloak_cls: MagicMock):
        for enabled, is_subscribed, access in (
            (True, 'true', FULL_ACCESS),
            (True, 'false', SIGN_IN_ONLY),
            (True, None, SIGN_IN_ONLY),
            (False, 'false', LOCKED),
        ):
            with self.subTest(enabled=enabled, is_subscribed=is_subscribed):
                mock_keycloak_cls.reset_mock()
                self._given_keycloak_user(mock_keycloak_cls, enabled=enabled, is_subscribed=is_subscribed)

                self.handler.sync(self.user, access)

                mock_keycloak_cls.return_value.update_user.assert_called_once()
                mock_keycloak_cls.return_value.logout_user.assert_not_called()

    def test_gaining_access_does_not_log_out(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=False, is_subscribed='false')

        self.handler.sync(self.user, SIGN_IN_ONLY)

        mock_keycloak_cls.return_value.logout_user.assert_not_called()

    def test_unknown_current_state_logs_out_whenever_access_is_restricted(self, mock_keycloak_cls: MagicMock):
        keycloak = mock_keycloak_cls.return_value
        keycloak.get_user.side_effect = GetUserError(oidc_id=OIDC_ID, error='down')

        self.handler.sync(self.user, SIGN_IN_ONLY)

        keycloak.update_user.assert_called_once_with(
            OIDC_ID, enabled=True, attributes={'is_active': 'true', 'is_subscribed': 'false'}, user_data=None
        )
        keycloak.logout_user.assert_called_once_with(OIDC_ID)

    def test_unknown_current_state_with_full_access_does_not_log_out(self, mock_keycloak_cls: MagicMock):
        keycloak = mock_keycloak_cls.return_value
        keycloak.get_user.side_effect = GetUserError(oidc_id=OIDC_ID, error='down')

        self.handler.sync(self.user, FULL_ACCESS)

        keycloak.update_user.assert_called_once()
        keycloak.logout_user.assert_not_called()

    def test_disable_failure_still_logs_out_then_raises_it(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='true')
        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.side_effect = UpdateUserError(error='boom', username=self.username)

        with self.assertRaises(UpdateUserError):
            self.handler.sync(self.user, LOCKED)

        keycloak.logout_user.assert_called_once_with(OIDC_ID)

    def test_update_failure_without_a_revocation_is_raised_unchanged(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='true')
        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.side_effect = UpdateUserError(error='boom', username=self.username)

        with self.assertRaises(UpdateUserError):
            self.handler.sync(self.user, FULL_ACCESS)

        keycloak.logout_user.assert_not_called()

    def test_logout_failure_alone_is_raised_unchanged(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='true')
        keycloak = mock_keycloak_cls.return_value
        keycloak.logout_user.side_effect = LogoutUserError(oidc_id=OIDC_ID, error='bang')

        with self.assertRaises(LogoutUserError):
            self.handler.sync(self.user, LOCKED)

    def test_both_failures_are_combined_into_one_error(self, mock_keycloak_cls: MagicMock):
        self._given_keycloak_user(mock_keycloak_cls, enabled=True, is_subscribed='true')
        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.side_effect = UpdateUserError(error='boom', username=self.username)
        keycloak.logout_user.side_effect = LogoutUserError(oidc_id=OIDC_ID, error='bang')

        with self.assertRaises(KeycloakError) as raised:
            self.handler.sync(self.user, LOCKED)

        self.assertIn('boom', str(raised.exception))
        self.assertIn('bang', str(raised.exception))
