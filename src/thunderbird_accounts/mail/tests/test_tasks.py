from thunderbird_accounts.celery.exceptions import TaskFailed
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail import tasks
from thunderbird_accounts.mail.exceptions import AccountNotFoundError
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.utils.tests.utils import build_mail_get_account


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

            results = tasks.update_quota_on_stalwart_account.run(
                username=f'test_user@{settings.PRIMARY_EMAIL_DOMAIN}', quota=settings.ONE_GIGABYTE_IN_BYTES
            )

            mail_client_mock.assert_called_once()
            instance_mock.update_quota.assert_called_once()

            self.assertEqual(results['task_status'], 'success')

    def test_with_none(self):
        """Passing None (the db default for quota in our schema) should actually pass 0 to stalwart.
        This is the same as unlimited / no quota in stalwart."""
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            instance_mock = Mock()
            mail_client_mock.return_value = instance_mock

            results = tasks.update_quota_on_stalwart_account.run(
                username=f'test_user@{settings.PRIMARY_EMAIL_DOMAIN}', quota=None
            )

            mail_client_mock.assert_called_once()
            instance_mock.update_quota.assert_called_once()

            self.assertEqual(results['task_status'], 'success')
            self.assertEqual(results['quota'], 0)


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

            User.objects.create(oidc_id=oidc_id, username=username_and_email, email=username_and_email)

            # Run sync so can look at the task results
            task_results = tasks.create_stalwart_account.run(
                oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
            )

            self.assertEqual(
                'success', task_results.get('task_status'), msg=f'Failed due to {task_results.get("reason")}'
            )

            mail_client_mock.assert_called_once()

            instance_mock.get_account.assert_called_with(username_and_email)
            instance_mock.save_email_addresses.assert_not_called()
            instance_mock.delete_email_addresses.assert_not_called()

            instance_mock.create_account.assert_called_once_with(
                [username_and_email, email_alias], username_and_email, None, None, quota
            )

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))
            self.assertEqual(mock_stalwart_pkid, task_results.get('stalwart_pkid'))

    def test_success_with_existing_account_and_email(self):
        """
        In case they have the reference to the stalwart account, but no actual data on stalwart's end,
        we need to make sure the stalwart account was created correctly,
        and the account and emails weren't modified outside of expectations.
        """
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
            account = Account.objects.create(name=user.username, active=True, quota=0, user=user, stalwart_id=None)
            email = Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY.value, account=account)
            alias = Email.objects.create(address=email_alias, type=Email.EmailType.ALIAS.value, account=account)

            self.assertEqual(None, account.stalwart_id)
            self.assertEqual(None, account.stalwart_updated_at)
            self.assertEqual(None, account.stalwart_created_at)

            # Run sync so can look at the task results
            task_results = tasks.create_stalwart_account.run(
                oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
            )

            self.assertEqual(
                'success', task_results.get('task_status'), msg=f'Failed due to {task_results.get("reason")}'
            )

            mail_client_mock.assert_called()

            instance_mock.get_account.assert_called_with(username_and_email)
            instance_mock.save_email_addresses.assert_not_called()
            instance_mock.delete_email_addresses.assert_not_called()

            instance_mock.create_account.assert_called_once_with(
                [username_and_email, email_alias], username_and_email, None, None, quota
            )

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))
            self.assertEqual(mock_stalwart_pkid, task_results.get('stalwart_pkid'))

            account.refresh_from_db()
            email.refresh_from_db()
            alias.refresh_from_db()

            # Account.stalwart_id is a string, in case stalwart gets weird with their ids later
            self.assertEqual(str(mock_stalwart_pkid), account.stalwart_id)
            self.assertIsNotNone(account.stalwart_updated_at)
            self.assertIsNotNone(account.stalwart_created_at)

            self.assertEqual(Email.EmailType.PRIMARY.value, email.type)
            self.assertEqual(Email.EmailType.ALIAS.value, alias.type)

    def test_success_account_already_exists_on_stalwart(self):
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            mock_stalwart_pkid = 1

            # Username is the app password login, and email is the primary email address
            username_and_email = f'test_user@{settings.PRIMARY_EMAIL_DOMAIN}'
            oidc_id = '1234'
            quota = settings.ONE_GIGABYTE_IN_BYTES * 100

            instance_mock = Mock()
            instance_mock.get_account.return_value = build_mail_get_account().json().get('data')
            instance_mock.create_account.return_value = mock_stalwart_pkid
            instance_mock.create_account.side_effect = AccountNotFoundError(username_and_email)
            mail_client_mock.return_value = instance_mock

            User.objects.create(oidc_id=oidc_id, username=username_and_email, email=username_and_email)

            # Run sync so can look at the task results
            task_results = tasks.create_stalwart_account.run(
                oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
            )

            self.assertEqual(
                'success', task_results.get('task_status'), msg=f'Failed due to {task_results.get("reason")}'
            )

            mail_client_mock.assert_called_once()
            instance_mock.get_account.assert_called_with(username_and_email)
            instance_mock.save_email_addresses.assert_called_once()
            instance_mock.delete_email_addresses.assert_called_once()

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))
            self.assertEqual(mock_stalwart_pkid, task_results.get('stalwart_pkid'))

    def test_creating_with_not_primary_domain(self):
        with patch('thunderbird_accounts.mail.tasks.MailClient', Mock()) as mail_client_mock:
            # Username is the app password login, and email is the primary email address
            domain = settings.ALLOWED_EMAIL_DOMAINS[1]
            username_and_email = f'test_user@{domain}'
            oidc_id = '1234'
            quota = settings.ONE_GIGABYTE_IN_BYTES * 100

            instance_mock = Mock()
            mail_client_mock.return_value = instance_mock

            # Run sync so can look at the task results
            with self.assertRaises(TaskFailed) as ex:
                tasks.create_stalwart_account.run(
                    oidc_id=oidc_id, username=username_and_email, email=username_and_email, quota=quota
                )
            task_results = ex.exception.other

            self.assertEqual(
                f'Cannot create Stalwart account with non-primary email domain: {domain}', ex.exception.reason
            )

            mail_client_mock.assert_called_once()

            instance_mock.get_account.assert_not_called()
            instance_mock.save_email_addresses.assert_not_called()
            instance_mock.delete_email_addresses.assert_not_called()

            self.assertEqual(username_and_email, task_results.get('email'))
            self.assertEqual(username_and_email, task_results.get('username'))
            self.assertEqual(oidc_id, task_results.get('oidc_id'))
