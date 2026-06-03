from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import freezegun

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.tasks import (
    tag_abandoned_cart_in_mailchimp,
    get_stale_incomplete_signup_users,
    purge_incomplete_signups,
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

        self.assertIn(user, get_stale_incomplete_signup_users())

    def test_includes_stale_user_without_subscription(self):
        user = self._create_user('stale-no-sub')

        self.assertIn(user, get_stale_incomplete_signup_users())

    def test_excludes_recent_user_without_subscription(self):
        user = self._create_user(
            'recent-no-sub',
            created_at=timezone.now() - timedelta(minutes=30),
        )

        self.assertNotIn(user, get_stale_incomplete_signup_users())

    def test_excludes_user_awaiting_payment_without_subscription(self):
        user = self._create_user('awaiting-payment', is_awaiting_payment_verification=True)

        self.assertNotIn(user, get_stale_incomplete_signup_users())

    def test_excludes_user_with_canceled_subscription(self):
        user = self._create_user('canceled-sub')
        Subscription.objects.create(user=user, status=Subscription.StatusValues.CANCELED)

        self.assertNotIn(user, get_stale_incomplete_signup_users())

    def test_excludes_user_with_active_subscription(self):
        user = self._create_user('active-sub')
        Subscription.objects.create(user=user, status=Subscription.StatusValues.ACTIVE)

        self.assertNotIn(user, get_stale_incomplete_signup_users())

    def test_excludes_test_account(self):
        user = self._create_user('test-account', is_test_account=True)

        self.assertNotIn(user, get_stale_incomplete_signup_users())

    def test_excludes_staff_user(self):
        user = self._create_user('staff-user', is_staff=True)

        self.assertNotIn(user, get_stale_incomplete_signup_users())

    @override_settings(ABANDONED_CART_TAG_HOURS=1)
    def test_includes_eligible_user_across_dst_spring_forward(self):
        # US Eastern clocks spring forward 2024-03-10 02:00 -> 03:00; cutoff uses UTC elapsed time.
        dst_now = datetime(2024, 3, 10, 7, 30, 0, tzinfo=ZoneInfo('UTC'))
        eligible_created_at = dst_now - timedelta(hours=2)
        with freezegun.freeze_time(dst_now):
            user = self._create_user('dst-eligible', created_at=eligible_created_at)

            self.assertIn(user, get_stale_incomplete_signup_users())


@freezegun.freeze_time(FROZEN_NOW)
@patch('thunderbird_accounts.authentication.tasks.add_or_tag_mailchimp_member')
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

    def test_tags_eligible_users(self, mock_add_or_tag):
        result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_add_or_tag.assert_called_once_with(
            'abandoned@example.com',
            settings.ABANDONED_CART_MAILCHIMP_TAG,
            language='en',
            error_context={'user_uuid': str(self.user.uuid)},
        )
        self.assertEqual(result['tagged'], 1)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['skipped'], 0)

    def test_skips_user_without_recovery_email(self, mock_add_or_tag):
        User.objects.filter(pk=self.user.pk).update(recovery_email=None)
        self.user.refresh_from_db()
        with patch(
            'thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users'
        ) as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user]

            result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_add_or_tag.assert_not_called()
        self.assertEqual(result['tagged'], 0)
        self.assertEqual(result['skipped'], 1)

    def test_counts_mailchimp_errors_and_continues(self, mock_add_or_tag):
        second_user = User.objects.create(
            username=f'abandoned-too@{self.subdomain}',
            email='abandoned-too@example.com',
            recovery_email='abandoned-too@example.com',
            oidc_id='abandoned-oidc-2',
        )
        User.objects.filter(pk=second_user.pk).update(
            created_at=timezone.now() - timedelta(hours=settings.ABANDONED_CART_TAG_HOURS + 1)
        )
        mock_add_or_tag.side_effect = [
            TaskFailed('mailchimp error', {'user_uuid': str(self.user.uuid)}),
            None,
        ]

        result = tag_abandoned_cart_in_mailchimp.apply().get()

        self.assertEqual(mock_add_or_tag.call_count, 2)
        self.assertEqual(result['tagged'], 1)
        self.assertEqual(result['errors'], 1)

    def test_skips_user_if_subscription_appears_after_initial_selection(self, mock_add_or_tag):
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        with patch(
            'thunderbird_accounts.authentication.tasks.get_stale_incomplete_signup_users'
        ) as mock_get_users:
            mock_get_users.return_value.iterator.return_value = [self.user]

            result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_add_or_tag.assert_not_called()
        self.assertEqual(result['tagged'], 0)
        self.assertEqual(result['skipped'], 1)

    @override_settings(USE_MAILCHIMP=False)
    def test_no_ops_when_mailchimp_disabled(self, mock_add_or_tag):
        result = tag_abandoned_cart_in_mailchimp.apply().get()

        mock_add_or_tag.assert_not_called()
        self.assertEqual(result['task_status'], 'skipped')
        self.assertEqual(result['tagged'], 0)


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

        result = purge_incomplete_signups.apply().get()

        mock_delete_user_data.assert_called_once()
        self.assertEqual(result['deleted'], 1)
        self.assertEqual(result['errors'], 0)

    def test_counts_partial_deletion_as_error(self, mock_delete_user_data):
        mock_delete_user_data.return_value = ['Keycloak: connection refused']

        result = purge_incomplete_signups.apply().get()

        self.assertEqual(result['deleted'], 0)
        self.assertEqual(result['errors'], 1)

    @override_settings(INCOMPLETE_SIGNUP_PURGE_HOURS=72)
    def test_skips_recent_users(self, mock_delete_user_data):
        User.objects.filter(pk=self.user.pk).update(created_at=timezone.now())

        result = purge_incomplete_signups.apply().get()

        mock_delete_user_data.assert_not_called()
        self.assertEqual(result['deleted'], 0)
