from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail import tasks
from thunderbird_accounts.mail.exceptions import AccountNotFoundError


class TaskTestCase(TestCase):
    celery_task_always_eager_setting: bool = False

    def setUp(self):
        super().setUp()

        self.celery_task_always_eager_setting = settings.CELERY_TASK_ALWAYS_EAGER

        # Make sure tasks run in sync
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        super().tearDown()

        settings.CELERY_TASK_ALWAYS_EAGER = self.celery_task_always_eager_setting


class UpdateQuotaOnStalwartAccountTestCase(TaskTestCase):
    def test_success(self):
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            instance_mock = Mock()
            mail_client_mock.return_value = instance_mock

            tasks.update_quota_on_stalwart_account.delay(
                username=f'test_user@{settings.PRIMARY_EMAIL_DOMAIN}', quota=settings.ONE_GIGABYTE_IN_BYTES
            )

            mail_client_mock.assert_called_once()
            instance_mock.update_quota.assert_called_once()


class CreateStalwartAccountTestCase(TaskTestCase):
    def test_success(self):
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            mock_stalwart_pkid = 1

            # Username is the app password login, and email is the primary email address
            username_and_email = f'test_user@{settings.PRIMARY_EMAIL_DOMAIN}'
            email_alias = f'test_user@{settings.ALLOWED_EMAIL_DOMAINS[1]}'
            oidc_id = '1234'
            quota = settings.ONE_GIGABYTE_IN_BYTES * 100

            instance_mock = Mock()
            instance_mock.create_account.return_value = mock_stalwart_pkid
            instance_mock.get_account.side_effect = AccountNotFoundError(username_and_email)
            mail_client_mock.return_value = instance_mock

            user = User.objects.create(oidc_id=oidc_id, username=username_and_email, email=username_and_email)

            # Run sync so can look at the task results
            task_results = tasks.create_stalwart_account.run(
                oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
            )

            self.assertEqual(
                'success', task_results.get('task_status'), msg=f'Failed due to {task_results.get("reason")}'
            )

            mail_client_mock.assert_called_once()

            instance_mock.create_account.assert_called_once_with(
                [username_and_email, email_alias], username_and_email, None, None, quota
            )

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))
            self.assertEqual(mock_stalwart_pkid, task_results.get('stalwart_pkid'))

    def test_account_already_exists(self):
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            # Username is the app password login, and email is the primary email address
            username_and_email = f'test_user@{settings.PRIMARY_EMAIL_DOMAIN}'
            oidc_id = '1234'
            quota = settings.ONE_GIGABYTE_IN_BYTES * 100

            # We intentionally don't mock get_account here
            instance_mock = Mock()
            mail_client_mock.return_value = instance_mock

            # Run sync so can look at the task results
            task_results = tasks.create_stalwart_account.run(
                oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
            )

            self.assertEqual('failed', task_results.get('task_status'))
            self.assertEqual('Username already exists in Stalwart.', task_results.get('reason'))

            mail_client_mock.assert_called_once()

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))

    def test_creating_with_not_primary_domain(self):
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            mock_stalwart_pkid = 1

            # Username is the app password login, and email is the primary email address
            domain = settings.ALLOWED_EMAIL_DOMAINS[1]
            username_and_email = f'test_user@{domain}'
            oidc_id = '1234'
            quota = settings.ONE_GIGABYTE_IN_BYTES * 100

            instance_mock = Mock()
            mail_client_mock.return_value = instance_mock

            # Run sync so can look at the task results
            task_results = tasks.create_stalwart_account.run(
                oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
            )

            self.assertEqual('failed', task_results.get('task_status'))
            self.assertEqual(
                f'Cannot create Stalwart account with non-primary email domain: {domain}', task_results.get('reason')
            )

            mail_client_mock.assert_called_once()

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))
