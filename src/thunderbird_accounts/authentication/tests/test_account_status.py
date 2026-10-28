from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase, override_settings

from thunderbird_accounts.authentication.account_status import (
    AccountStatusHandler,
    UserAccess,
    set_user_active,
    sync_user_access,
    user_access,
)
from thunderbird_accounts.authentication.exceptions import LogoutUserError, UpdateUserError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.exceptions import AccountNotFoundError
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.subscription.models import Subscription

OIDC_ID = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'
KEYCLOAK_CLIENT = 'thunderbird_accounts.authentication.keycloak_account_status.KeycloakClient'
MAIL_CLIENT = 'thunderbird_accounts.mail.stalwart_account_status.MailClient'

# Order in which the fake handlers below were run, reset by the tests that use them.
HANDLER_CALLS: list[tuple[str, UserAccess]] = []


class RecordingHandler(AccountStatusHandler):
    label = 'Recording'

    def sync(self, user, access):
        HANDLER_CALLS.append((self.label, access))


class SecondRecordingHandler(RecordingHandler):
    label = 'Second'


class FailingHandler(AccountStatusHandler):
    label = 'Failing'

    def sync(self, user, access):
        raise ValueError('kaboom')


FAKE_HANDLERS = [
    f'{__name__}.RecordingHandler',
    f'{__name__}.FailingHandler',
    f'{__name__}.SecondRecordingHandler',
]


def _create_subscription(user: User, status: Subscription.StatusValues) -> Subscription:
    return Subscription.objects.create(user=user, status=status, paddle_id='sub_1', paddle_customer_id='ctm_1')


class UserAccessTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username=f'person@{settings.PRIMARY_EMAIL_DOMAIN}', email='r@example.com')

    def test_active_user_with_active_subscription_has_everything(self):
        _create_subscription(self.user, Subscription.StatusValues.ACTIVE)
        self.assertEqual(user_access(self.user), UserAccess(can_sign_in=True, has_services=True))

    def test_past_due_subscription_still_grants_services(self):
        _create_subscription(self.user, Subscription.StatusValues.PAST_DUE)
        self.assertEqual(user_access(self.user), UserAccess(can_sign_in=True, has_services=True))

    def test_paused_subscription_keeps_sign_in_but_not_services(self):
        _create_subscription(self.user, Subscription.StatusValues.PAUSED)
        self.assertEqual(user_access(self.user), UserAccess(can_sign_in=True, has_services=False))

    def test_no_subscription_keeps_sign_in_but_not_services(self):
        self.assertEqual(user_access(self.user), UserAccess(can_sign_in=True, has_services=False))

    def test_inactive_user_has_nothing_even_when_subscribed(self):
        _create_subscription(self.user, Subscription.StatusValues.ACTIVE)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(user_access(self.user), UserAccess(can_sign_in=False, has_services=False))

    def test_reads_the_database_not_the_instance(self):
        _create_subscription(self.user, Subscription.StatusValues.ACTIVE)
        self.user.is_active = False  # not saved
        self.assertEqual(user_access(self.user), UserAccess(can_sign_in=True, has_services=True))


@patch(MAIL_CLIENT)
@patch(KEYCLOAK_CLIENT)
class SetUserActiveTestCase(TestCase):
    def setUp(self):
        self.username = f'person@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.user = User.objects.create(username=self.username, oidc_id=OIDC_ID, email='recovery@example.com')
        self.account = Account.objects.create(name=self.username, user=self.user)
        Email.objects.create(address=self.username, type=Email.EmailType.PRIMARY, account=self.account)
        self.subscription = _create_subscription(self.user, Subscription.StatusValues.ACTIVE)

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

    def test_reactivation_without_an_entitled_subscription_keeps_stalwart_locked(
        self, mock_keycloak_cls: MagicMock, mock_mail_cls
    ):
        self.subscription.status = Subscription.StatusValues.PAUSED
        self.subscription.save()
        set_user_active(self.user, False)
        mock_keycloak_cls.reset_mock()
        mock_mail_cls.reset_mock()

        errors = set_user_active(self.user, True)

        self.assertEqual(errors, [])
        self.account.refresh_from_db()
        self.assertFalse(self.account.active)
        mock_keycloak_cls.return_value.update_user.assert_called_once_with(OIDC_ID, enabled=True)
        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, False)

    def test_keycloak_failure_is_reported_and_stalwart_still_updated(self, mock_keycloak_cls: MagicMock, mock_mail_cls):
        mock_keycloak_cls.return_value.update_user.side_effect = UpdateUserError(error='boom', username=self.username)

        errors = set_user_active(self.user, False)

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('Keycloak:'), errors)
        mock_keycloak_cls.return_value.logout_user.assert_called_once_with(OIDC_ID)
        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_keycloak_update_and_logout_failures_are_both_reported(self, mock_keycloak_cls: MagicMock, mock_mail_cls):
        keycloak = mock_keycloak_cls.return_value
        keycloak.update_user.side_effect = UpdateUserError(error='boom', username=self.username)
        keycloak.logout_user.side_effect = LogoutUserError(oidc_id=OIDC_ID, error='bang')

        errors = set_user_active(self.user, False)

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('Keycloak:'), errors)
        self.assertIn('boom', errors[0])
        self.assertIn('bang', errors[0])
        mock_mail_cls.return_value.set_account_active.assert_called_once_with(self.username, False)

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


@override_settings(USER_ACCOUNT_STATUS_HANDLERS=FAKE_HANDLERS)
@patch('thunderbird_accounts.authentication.account_status.sentry_sdk')
class SyncUserAccessTestCase(TestCase):
    def setUp(self):
        HANDLER_CALLS.clear()
        self.user = User.objects.create(username=f'person@{settings.PRIMARY_EMAIL_DOMAIN}', email='r@example.com')
        _create_subscription(self.user, Subscription.StatusValues.ACTIVE)

    def test_handlers_run_in_order_and_a_failure_does_not_stop_the_others(self, mock_sentry: MagicMock):
        errors = sync_user_access(self.user)

        self.assertEqual(errors, ['Failing: kaboom'])
        expected = UserAccess(can_sign_in=True, has_services=True)
        self.assertEqual(HANDLER_CALLS, [('Recording', expected), ('Second', expected)])
        self.assertIsInstance(mock_sentry.capture_exception.call_args.args[0], ValueError)

    def test_set_user_active_persists_the_flag_even_when_a_handler_fails(self, mock_sentry: MagicMock):
        errors = set_user_active(self.user, False)

        self.assertEqual(errors, ['Failing: kaboom'])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        expected = UserAccess(can_sign_in=False, has_services=False)
        self.assertEqual(HANDLER_CALLS, [('Recording', expected), ('Second', expected)])

