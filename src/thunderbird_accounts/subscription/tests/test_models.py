from unittest.mock import patch, Mock

from django.test import TestCase

from thunderbird_accounts.subscription.models import Plan


class PlanSaveTestCase(TestCase):
    def test_mail_storage_gb_task_is_not_called(self):
        """Ensure if we do an update to a different field we don't trigger the task"""
        with patch('thunderbird_accounts.subscription.tasks.update_thundermail_quota', Mock()) as event_mock:
            plan = Plan.objects.create(
                name='Plan 123',
                mail_storage_gb=1,
            )

            event_mock.delay.assert_not_called()

            plan.mail_address_count = 20
            plan.save()

            event_mock.delay.assert_not_called()

    def test_mail_storage_gb_task_is_called(self):
        """Ensure updating the field triggers the task"""
        with patch('thunderbird_accounts.subscription.tasks.update_thundermail_quota', Mock()) as event_mock:
            plan = Plan.objects.create(
                name='Plan 123',
                mail_storage_gb=100,
            )

            event_mock.delay.assert_not_called()

            plan.mail_storage_gb = 1
            plan.save()

            event_mock.delay.assert_called()
