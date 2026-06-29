import uuid
from django.contrib.auth.models import Group
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import freezegun

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from thunderbird_accounts.authentication.models import User, AllowListEntry
from thunderbird_accounts.authentication.tasks import (
    tag_abandoned_cart_in_mailchimp,
    get_stale_incomplete_signup_users,
    purge_incomplete_signups,
    purge_stale_test_allow_list_entries,
)
from thunderbird_accounts.celery.exceptions import TaskFailed
from thunderbird_accounts.subscription.models import Subscription


FROZEN_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=ZoneInfo('UTC'))


@freezegun.freeze_time(FROZEN_NOW)
class GetStaleIncompleteSignupUsersTestCase(TestCase):
    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        self.cutoff_age = timedelta(hours=settings.INCOMPLETE_SIGNUP_PURGE_HOURS + 1)
        self.stale_created_at = timezone.now() - self.cutoff_age
        self.eligible_created_at = timezone.now() - timedelta(hours=settings.ABANDONED_CART_TAG_HOURS + 1)

    def _create_user(self, username_suffix, **kwargs):
        defaults = {
            'username': f'{username_suffix}@{self.subdomain}',
            'email': f'{username_suffix}@example.com',
            'recovery_email': f'{username_suffix}@example.com',
            'oidc_id': f'oidc-{username_suffix}',
            'created_at': self.stale_created_at,
        }
        defaults.update(kwargs)
        created_at = defaults.pop('created_at')
        user = User(**defaults)
        user.save()
        User.objects.filter(pk=user.pk).update(created_at=created_at)
        user.refresh_from_db()
        return user

    def test_includes_eligible_user_without_subscription(self):
        user = self._create_user('abandoned-no-sub', created_at=self.eligible_created_at)

        self.assertIn(
            user,
            get_stale_incomplete_signup_users(settings.ABANDONED_CART_TAG_HOURS),
        )

    def test_includes_stale_user_without_subscription(self):
        user = self._create_user('stale-no-sub')

        self.assertIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    def test_excludes_stale_user_awaiting_payment_without_subscription(self):
        user = self._create_user('stale-awaiting', is_awaiting_payment_verification=True)

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    def test_excludes_recent_user_without_subscription(self):
        user = self._create_user(
            'recent-no-sub',
            created_at=timezone.now() - timedelta(minutes=30),
        )

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.ABANDONED_CART_TAG_HOURS),
        )

    def test_excludes_user_awaiting_payment_without_subscription(self):
        user = self._create_user('awaiting-payment', is_awaiting_payment_verification=True)

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    def test_excludes_user_with_canceled_subscription(self):
        user = self._create_user('canceled-sub')
        Subscription.objects.create(user=user, status=Subscription.StatusValues.CANCELED)

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    def test_excludes_user_with_active_subscription(self):
        user = self._create_user('active-sub')
        Subscription.objects.create(user=user, status=Subscription.StatusValues.ACTIVE)

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    def test_excludes_test_account(self):
        user = self._create_user('test-account', is_test_account=True)

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    def test_excludes_staff_user(self):
        user = self._create_user('staff-user', is_staff=True)

        self.assertNotIn(
            user,
            get_stale_incomplete_signup_users(settings.INCOMPLETE_SIGNUP_PURGE_HOURS),
        )

    @override_settings(ABANDONED_CART_TAG_HOURS=1)
    def test_includes_eligible_user_across_dst_spring_forward(self):
        # US Eastern clocks spring forward 2024-03-10 02:00 -> 03:00; cutoff uses UTC elapsed time.
        dst_now = datetime(2024, 3, 10, 7, 30, 0, tzinfo=ZoneInfo('UTC'))
        eligible_created_at = dst_now - timedelta(hours=2)
        with freezegun.freeze_time(dst_now):
            user = self._create_user('dst-eligible', created_at=eligible_created_at)

            self.assertIn(
                user,
                get_stale_incomplete_signup_users(settings.ABANDONED_CART_TAG_HOURS),
            )


@freezegun.freeze_time(FROZEN_NOW)
@patch('thunderbird_accounts.authentication.tasks.MailchimpClient')
class TagAbandonedCartInMailchimpTaskTestCase(TestCase):
    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        eligible_created_at = timezone.now() - timedelta(hours=settings.ABANDONED_CART_TAG_HOURS + 1)
        self.user = User.objects.create(
            username=f'abandoned@{self.subdomain}',
            email='abandoned@example.com',
            recovery_email='abandoned@example.com',
            oidc_id='abandoned-oidc-1',
        )
        User.objects.filter(pk=self.user.pk).update(created_at=eligible_created_at)

    def test_tags_eligible_users(self, mock_client_cls):
        result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_client_cls.return_value.add_or_tag_member.assert_called_once_with(
            'abandoned@example.com',
            settings.ABANDONED_CART_MAILCHIMP_TAG,
            language='en',
            error_context={'user_uuid': str(self.user.uuid)},
        )
        self.assertEqual(result['tagged'], 1)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['skipped'], 0)

    def test_skips_user_without_recovery_email(self, mock_client_cls):
        User.objects.filter(pk=self.user.pk).update(recovery_email=None)
        self.user.refresh_from_db()
        with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user]

            result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_client_cls.return_value.add_or_tag_member.assert_not_called()
        self.assertEqual(result['tagged'], 0)
        self.assertEqual(result['skipped'], 1)

    def test_counts_mailchimp_errors_and_continues(self, mock_client_cls):
        second_user = User.objects.create(
            username=f'abandoned-too@{self.subdomain}',
            email='abandoned-too@example.com',
            recovery_email='abandoned-too@example.com',
            oidc_id='abandoned-oidc-2',
        )
        User.objects.filter(pk=second_user.pk).update(
            created_at=timezone.now() - timedelta(hours=settings.ABANDONED_CART_TAG_HOURS + 1)
        )
        mock_client_cls.return_value.add_or_tag_member.side_effect = [
            TaskFailed('mailchimp error', {'user_uuid': str(self.user.uuid)}),
            None,
        ]

        result = tag_abandoned_cart_in_mailchimp.apply().get()

        self.assertEqual(mock_client_cls.return_value.add_or_tag_member.call_count, 2)
        self.assertEqual(result['tagged'], 1)
        self.assertEqual(result['errors'], 1)

    def test_skips_user_if_subscription_appears_after_initial_selection(self, mock_client_cls):
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user]

            result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_client_cls.return_value.add_or_tag_member.assert_not_called()
        self.assertEqual(result['tagged'], 0)
        self.assertEqual(result['skipped'], 1)

    @override_settings(USE_MAILCHIMP=False)
    def test_no_ops_when_mailchimp_disabled(self, mock_client_cls):
        result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_client_cls.return_value.add_or_tag_member.assert_not_called()
        self.assertEqual(result['task_status'], 'skipped')
        self.assertEqual(result['tagged'], 0)


# TEMP: Until #1028 is no longer needed
# @patch('thunderbird_accounts.authentication.tasks.delete_user_data')
# class PurgeIncompleteSignupsTaskTestCase(TestCase):
#     def setUp(self):
#         self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
#         stale_created_at = timezone.now() - timedelta(hours=settings.INCOMPLETE_SIGNUP_PURGE_HOURS + 1)
#         self.user = User.objects.create(
#             username=f'purge-me@{self.subdomain}',
#             email='purge-me@example.com',
#             oidc_id='purge-oidc-1',
#         )
#         User.objects.filter(pk=self.user.pk).update(created_at=stale_created_at)

#     def test_deletes_stale_incomplete_users(self, mock_delete_user_data):
#         mock_delete_user_data.return_value = []

#         result = purge_incomplete_signups.apply().get()

#         mock_delete_user_data.assert_called_once()
#         self.assertEqual(result['deleted'], 1)
#         self.assertEqual(result['errors'], 0)

#     def test_counts_partial_deletion_as_error(self, mock_delete_user_data):
#         mock_delete_user_data.return_value = ['Keycloak: connection refused']

#         result = purge_incomplete_signups.apply().get()

#         self.assertEqual(result['deleted'], 0)
#         self.assertEqual(result['errors'], 1)

#     def test_skips_user_if_subscription_appears_after_initial_selection(self, mock_delete_user_data):
#         Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
#         with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
#             mock_get_users.return_value.iterator.return_value = [self.user]

#             result = purge_incomplete_signups.apply().get()

#         mock_delete_user_data.assert_not_called()
#         self.assertEqual(result['deleted'], 0)
#         self.assertEqual(result['errors'], 0)
#         self.assertEqual(result['skipped'], 1)

#     def test_continues_after_unexpected_delete_exception(self, mock_delete_user_data):
#         second_user = User.objects.create(
#             username=f'purge-me-too@{self.subdomain}',
#             email='purge-me-too@example.com',
#             oidc_id='purge-oidc-2',
#         )
#         User.objects.filter(pk=second_user.pk).update(
#             created_at=timezone.now() - timedelta(hours=settings.INCOMPLETE_SIGNUP_PURGE_HOURS + 1)
#         )
#         mock_delete_user_data.side_effect = [RuntimeError('boom'), []]
#         with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
#             mock_get_users.return_value.iterator.return_value = [self.user, second_user]

#             result = purge_incomplete_signups.apply().get()

#         self.assertEqual(mock_delete_user_data.call_count, 2)
#         self.assertEqual(result['deleted'], 1)
#         self.assertEqual(result['errors'], 1)

#     @override_settings(INCOMPLETE_SIGNUP_PURGE_HOURS=120)
#     def test_skips_recent_users(self, mock_delete_user_data):
#         User.objects.filter(pk=self.user.pk).update(created_at=timezone.now())

#         result = purge_incomplete_signups.apply().get()

#         mock_delete_user_data.assert_not_called()
#         self.assertEqual(result['deleted'], 0)

#     def test_does_not_delete_user_awaiting_payment_verification(self, mock_delete_user_data):
#         self.user.is_awaiting_payment_verification = True
#         self.user.save()

#         result = purge_incomplete_signups.apply().get()

#         mock_delete_user_data.assert_not_called()
#         self.assertEqual(result['deleted'], 0)

#     def test_skips_user_if_awaiting_payment_after_initial_selection(self, mock_delete_user_data):
#         self.user.is_awaiting_payment_verification = True
#         self.user.save()
#         with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
#             mock_get_users.return_value.iterator.return_value = [self.user]

#             result = purge_incomplete_signups.apply().get()

#         mock_delete_user_data.assert_not_called()
#         self.assertEqual(result['skipped'], 1)


@patch('thunderbird_accounts.authentication.tasks.delete_user_data')
class PurgeIncompleteSignupsTaskTestCase(TestCase):
    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        stale_created_at = timezone.now() - timedelta(hours=settings.INCOMPLETE_SIGNUP_PURGE_HOURS + 1)
        self.user = User.objects.create(
            username=f'purge-me@{self.subdomain}',
            email='purge-me@example.com',
            oidc_id='purge-oidc-1',
        )
        User.objects.filter(pk=self.user.pk).update(created_at=stale_created_at)

    def test_deletes_stale_incomplete_users(self, mock_delete_user_data):
        mock_delete_user_data.return_value = []

        self.assertEqual(self.user.groups.count(), 0)

        result = purge_incomplete_signups.apply().get()

        # Test the group change
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 1)

        # Ensure our delete user data function did not run
        mock_delete_user_data.assert_not_called()

        # Ensure that deleted is 1
        self.assertEqual(result['deleted'], 1)
        self.assertEqual(result['errors'], 0)

    def test_counts_partial_deletion_as_error(self, mock_delete_user_data):
        mock_delete_user_data.return_value = ['Keycloak: connection refused']

        self.assertEqual(self.user.groups.count(), 0)

        result = purge_incomplete_signups.apply().get()

        # Test the group change
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 1)

        self.assertEqual(result['deleted'], 1)
        self.assertEqual(result['errors'], 0)

    def test_skips_user_if_subscription_appears_after_initial_selection(self, mock_delete_user_data):
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user]

            result = purge_incomplete_signups.apply().get()

        # Test the group change
        self.assertEqual(self.user.groups.count(), 0)
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)

        mock_delete_user_data.assert_not_called()
        self.assertEqual(result['deleted'], 0)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['skipped'], 1)

    def test_continues_after_unexpected_delete_exception(self, mock_delete_user_data):
        second_user = User.objects.create(
            username=f'purge-me-too@{self.subdomain}',
            email='purge-me-too@example.com',
            oidc_id='purge-oidc-2',
        )

        self.assertEqual(second_user.groups.count(), 0)

        User.objects.filter(pk=second_user.pk).update(
            created_at=timezone.now() - timedelta(hours=settings.INCOMPLETE_SIGNUP_PURGE_HOURS + 1)
        )
        mock_delete_user_data.side_effect = [RuntimeError('boom'), []]
        with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user, second_user]

            result = purge_incomplete_signups.apply().get()

        # Test the group change
        second_user.refresh_from_db()
        self.assertEqual(second_user.groups.count(), 1)

        self.assertEqual(mock_delete_user_data.call_count, 0)  # Not called!
        self.assertEqual(result['deleted'], 2)  # This is two because we never actually
        # call delete user data so there can never be an error
        self.assertEqual(result['errors'], 0)

    @override_settings(INCOMPLETE_SIGNUP_PURGE_HOURS=120)
    def test_skips_recent_users(self, mock_delete_user_data):
        User.objects.filter(pk=self.user.pk).update(created_at=timezone.now())

        self.assertEqual(self.user.groups.count(), 0)

        result = purge_incomplete_signups.apply().get()

        # Test the group change
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)

        mock_delete_user_data.assert_not_called()
        self.assertEqual(result['deleted'], 0)

    def test_does_not_delete_user_awaiting_payment_verification(self, mock_delete_user_data):
        self.user.is_awaiting_payment_verification = True
        self.user.save()

        self.assertEqual(self.user.groups.count(), 0)

        result = purge_incomplete_signups.apply().get()

        # Test the group change
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)

        mock_delete_user_data.assert_not_called()
        self.assertEqual(result['deleted'], 0)

    def test_skips_user_if_awaiting_payment_after_initial_selection(self, mock_delete_user_data):
        self.user.is_awaiting_payment_verification = True
        self.user.save()

        self.assertEqual(self.user.groups.count(), 0)

        with patch('thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users') as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user]

            result = purge_incomplete_signups.apply().get()

        # Test the group change
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)

        mock_delete_user_data.assert_not_called()
        self.assertEqual(result['skipped'], 1)

    def test_add_group_if_not_found(self, mock_delete_user_data):
        mock_delete_user_data.return_value = []

        # Group doesn't exist
        group = Group.objects.filter(name='Users to Purge').first()
        self.assertIsNone(group)

        purge_incomplete_signups.apply().get()

        # Group should exist now
        group = Group.objects.filter(name='Users to Purge').first()
        self.assertIsNotNone(group)

        # Ensure our delete user data function did not run
        mock_delete_user_data.assert_not_called()

    def test_removes_from_group_if_later_matches_criteria(self, mock_delete_user_data):
        self.assertEqual(self.user.groups.count(), 0)
        purge_incomplete_signups.apply().get()
        mock_delete_user_data.assert_not_called()

        # Test the group change
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 1)

        # Adjust the user to be "safe" from this task
        self.user.is_awaiting_payment_verification = True
        self.user.save()

        # Run the task again
        purge_incomplete_signups.apply().get()
        mock_delete_user_data.assert_not_called()

        # We're out of the group!
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)


@patch('thunderbird_accounts.authentication.tasks.delete_user_data')
class PurgeStaleAllowListEntryTestCase(TestCase):
    def setUp(self):
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        self.stale_created_at = timezone.now() - timedelta(minutes=settings.TEST_ALLOW_LIST_ENTRIES_STALE_TIME_IN_MINS)

    def _create_allow_list_entry(self, is_test_entry=True, updated_at=None):
        allow_list_entry = AllowListEntry.objects.create(
            email=f'{uuid.uuid4()}@example.com', is_test_entry=is_test_entry
        )
        if allow_list_entry and updated_at:
            AllowListEntry.objects.filter(uuid=allow_list_entry.uuid).update(created_at=updated_at)
            allow_list_entry.refresh_from_db()
        return allow_list_entry

    def _create_user(self, email=None, username=None, oidc_id=None, **kwargs):
        if not email:
            email = f'{uuid.uuid4()}@example.com'
        if not username:
            username = f'{uuid.uuid4()}@{self.subdomain}'
        if not oidc_id:
            oidc_id = f'{uuid.uuid4()}'
        return User.objects.create(username=username, email=email, oidc_id=oidc_id, **kwargs)

    def test_success(self, mock_delete_user_data):
        mock_delete_user_data.return_value = []

        allow_list_entry = self._create_allow_list_entry(is_test_entry=True, updated_at=self.stale_created_at)
        user = self._create_user(email=allow_list_entry.email)
        allow_list_entry.user_id = user.uuid
        allow_list_entry.save()

        allow_list_entry_without_user = self._create_allow_list_entry(
            is_test_entry=True, updated_at=self.stale_created_at
        )

        result = purge_stale_test_allow_list_entries.apply().get()

        mock_delete_user_data.assert_called_once_with(user)

        self.assertEqual(result['users_deleted'], 1)
        self.assertEqual(result['deleted'], 2)
        self.assertEqual(result['errors'], 0)

        with self.assertRaises(AllowListEntry.DoesNotExist):
            allow_list_entry.refresh_from_db()
        with self.assertRaises(AllowListEntry.DoesNotExist):
            allow_list_entry_without_user.refresh_from_db()
        # Note: User isn't destroyed destroyed because we're mocking the call

    def test_non_test_entries_are_left_alone(self, mock_delete_user_data):
        mock_delete_user_data.return_value = []

        allow_list_entry = self._create_allow_list_entry(is_test_entry=False, updated_at=self.stale_created_at)
        user = self._create_user(email=allow_list_entry.email)
        allow_list_entry.user_id = user.uuid
        allow_list_entry.save()

        allow_list_entry_without_user = self._create_allow_list_entry(
            is_test_entry=False, updated_at=self.stale_created_at
        )

        result = purge_stale_test_allow_list_entries.apply().get()

        mock_delete_user_data.assert_not_called()

        self.assertEqual(result['users_deleted'], 0)
        self.assertEqual(result['deleted'], 0)
        self.assertEqual(result['errors'], 0)

        allow_list_entry.refresh_from_db()
        allow_list_entry_without_user.refresh_from_db()

        self.assertIsNotNone(allow_list_entry)
        self.assertIsNotNone(allow_list_entry_without_user)

    def test_fresh_entry_is_left_alone(self, mock_delete_user_data):
        mock_delete_user_data.return_value = []

        allow_list_entry = self._create_allow_list_entry(is_test_entry=True)
        user = self._create_user(email=allow_list_entry.email)
        allow_list_entry.user_id = user.uuid
        allow_list_entry.save()

        result = purge_stale_test_allow_list_entries.apply().get()

        mock_delete_user_data.assert_not_called()

        self.assertEqual(result['users_deleted'], 0)
        self.assertEqual(result['deleted'], 0)
        self.assertEqual(result['errors'], 0)

        self.assertIsNotNone(allow_list_entry)
