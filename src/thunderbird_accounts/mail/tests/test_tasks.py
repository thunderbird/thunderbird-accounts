from thunderbird_accounts.celery.exceptions import TaskFailed
from unittest.mock import patch, Mock, call

from django.conf import settings
from django.test import TestCase, override_settings

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail import tasks
from thunderbird_accounts.mail.exceptions import AccountNotFoundError, HostedDkimDeleteRetry, HostedDkimPublishRetry
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.core.tests.utils import build_mail_get_account


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


class PublishHostedDkimDNSRecordsTestCase(TaskTestCase):
    @override_settings(
        HOSTED_DKIM_CLOUDFLARE_ENABLED=False,
        HOSTED_DKIM_DOMAIN='dkim.example.net',
        HOSTED_DKIM_SELECTORS=['tm1', 'tm2', 'tm3'],
    )
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    def test_logs_records_when_cloudflare_publication_disabled(self, mail_client_mock, cloudflare_client_mock):
        dkim_records = [
            {'type': 'TXT', 'name': 'tm1._domainkey.example.com.', 'content': 'v=DKIM1; p=rsa'},
            {'type': 'TXT', 'name': 'tm2._domainkey.example.com.', 'content': 'v=DKIM1; p=ed25519'},
        ]
        mail_client_mock.return_value.get_dkim_dns_records.return_value = dkim_records

        with self.assertLogs(level='INFO') as logs:
            results = tasks.publish_hosted_dkim_dns_records.run(domain_name='example.com')

        self.assertEqual(results['task_status'], 'success')
        self.assertTrue(results['skipped'])
        self.assertEqual(
            [
                {'type': 'TXT', 'name': 'tm1.example.com.dkim.example.net', 'content': 'v=DKIM1; p=rsa'},
                {'type': 'TXT', 'name': 'tm2.example.com.dkim.example.net', 'content': 'v=DKIM1; p=ed25519'},
            ],
            results['records'],
        )
        cloudflare_client_mock.assert_not_called()
        self.assertIn(
            'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS update to set '
            '"TXT tm1.example.com.dkim.example.net v=DKIM1; p=rsa"',
            logs.output[0],
        )
        self.assertIn(
            'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS update to set '
            '"TXT tm2.example.com.dkim.example.net v=DKIM1; p=ed25519"',
            logs.output[1],
        )

    @override_settings(
        HOSTED_DKIM_CLOUDFLARE_ENABLED=True,
        HOSTED_DKIM_CLOUDFLARE_ZONE_ID='zone-id',
        HOSTED_DKIM_CLOUDFLARE_API_TOKEN='secret',
        HOSTED_DKIM_DOMAIN='dkim.example.net',
        HOSTED_DKIM_SELECTORS=['tm1', 'tm2', 'tm3'],
    )
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    def test_publishes_stalwart_dkim_records_to_hosted_domain(self, mail_client_mock, cloudflare_client_mock):
        dkim_records = [
            {'type': 'TXT', 'name': 'tm1._domainkey.example.com.', 'content': 'v=DKIM1; p=rsa'},
            {'type': 'TXT', 'name': 'tm2._domainkey.example.com.', 'content': 'v=DKIM1; p=ed25519'},
        ]
        hosted_records = [
            {'type': 'TXT', 'name': 'tm1.example.com.dkim.example.net', 'content': 'v=DKIM1; p=rsa'},
            {'type': 'TXT', 'name': 'tm2.example.com.dkim.example.net', 'content': 'v=DKIM1; p=ed25519'},
        ]
        mail_client_mock.return_value.get_dkim_dns_records.return_value = dkim_records

        results = tasks.publish_hosted_dkim_dns_records.run(domain_name='example.com')

        mail_client_mock.return_value.get_dkim_dns_records.assert_called_once_with('example.com')
        cloudflare_client_mock.return_value.upsert_txt_record.assert_has_calls(
            [
                call('tm1.example.com.dkim.example.net', 'v=DKIM1; p=rsa'),
                call('tm2.example.com.dkim.example.net', 'v=DKIM1; p=ed25519'),
            ]
        )
        published_names = [
            args[0] for args, _kwargs in cloudflare_client_mock.return_value.upsert_txt_record.call_args_list
        ]
        self.assertNotIn('tm1._domainkey.example.com.', published_names)
        self.assertFalse(any('._domainkey.' in name for name in published_names))
        self.assertEqual(results['task_status'], 'success')
        self.assertFalse(results['skipped'])
        self.assertEqual(hosted_records, results['records'])

    @override_settings(HOSTED_DKIM_CLOUDFLARE_ENABLED=False)
    @patch('thunderbird_accounts.mail.tasks.sentry_sdk.set_context')
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    def test_retries_with_context_when_stalwart_fetch_fails(self, mail_client_mock, set_sentry_context_mock):
        mail_client_mock.return_value.get_dkim_dns_records.side_effect = RuntimeError('Stalwart unavailable')

        with self.assertRaises(HostedDkimPublishRetry) as cm:
            tasks.publish_hosted_dkim_dns_records.run(domain_name='example.com')

        self.assertEqual('example.com', cm.exception.domain)
        self.assertEqual('fetch_stalwart_dkim_dns_records', cm.exception.phase)
        self.assertEqual('Stalwart unavailable', cm.exception.reason)
        self.assertEqual('example.com', cm.exception.context['domain'])
        self.assertEqual('fetch_stalwart_dkim_dns_records', cm.exception.context['phase'])
        self.assertEqual('RuntimeError', cm.exception.context['error_type'])
        set_sentry_context_mock.assert_called_once_with('hosted_dkim_publish_retry', cm.exception.context)


class DeleteHostedDkimDNSRecordsTestCase(TaskTestCase):
    @override_settings(
        HOSTED_DKIM_CLOUDFLARE_ENABLED=False,
        HOSTED_DKIM_DOMAIN='dkim.example.net',
        HOSTED_DKIM_SELECTORS=['tm1', 'tm2', 'tm3'],
    )
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    def test_logs_records_when_cloudflare_deletion_disabled(self, cloudflare_client_mock):
        with self.assertLogs(level='INFO') as logs:
            results = tasks.delete_hosted_dkim_dns_records.run(domain_name='example.com')

        self.assertEqual(results['task_status'], 'success')
        self.assertTrue(results['skipped'])
        self.assertEqual(
            [
                {'type': 'TXT', 'name': 'tm1.example.com.dkim.example.net'},
                {'type': 'TXT', 'name': 'tm2.example.com.dkim.example.net'},
                {'type': 'TXT', 'name': 'tm3.example.com.dkim.example.net'},
            ],
            results['records'],
        )
        cloudflare_client_mock.assert_not_called()
        self.assertIn(
            '[delete_hosted_dkim_dns_records] '
            'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS delete for '
            '"TXT tm1.example.com.dkim.example.net"',
            logs.output[0],
        )
        self.assertIn(
            '[delete_hosted_dkim_dns_records] '
            'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS delete for '
            '"TXT tm2.example.com.dkim.example.net"',
            logs.output[1],
        )
        self.assertIn(
            '[delete_hosted_dkim_dns_records] '
            'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS delete for '
            '"TXT tm3.example.com.dkim.example.net"',
            logs.output[2],
        )

    @override_settings(
        HOSTED_DKIM_CLOUDFLARE_ENABLED=True,
        HOSTED_DKIM_CLOUDFLARE_ZONE_ID='zone-id',
        HOSTED_DKIM_CLOUDFLARE_API_TOKEN='secret',
        HOSTED_DKIM_DOMAIN='dkim.example.net',
        HOSTED_DKIM_SELECTORS=['tm1', 'tm2', 'tm3'],
    )
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    def test_deletes_hosted_dkim_records_from_cloudflare(self, cloudflare_client_mock):
        cloudflare_client_mock.return_value.delete_txt_records.side_effect = [['record-1'], ['record-2'], []]

        results = tasks.delete_hosted_dkim_dns_records.run(domain_name='example.com')

        cloudflare_client_mock.return_value.delete_txt_records.assert_has_calls(
            [
                call('tm1.example.com.dkim.example.net'),
                call('tm2.example.com.dkim.example.net'),
                call('tm3.example.com.dkim.example.net'),
            ]
        )
        self.assertEqual(results['task_status'], 'success')
        self.assertFalse(results['skipped'])
        self.assertEqual(
            [
                {
                    'type': 'TXT',
                    'name': 'tm1.example.com.dkim.example.net',
                    'deleted_record_ids': ['record-1'],
                },
                {
                    'type': 'TXT',
                    'name': 'tm2.example.com.dkim.example.net',
                    'deleted_record_ids': ['record-2'],
                },
                {
                    'type': 'TXT',
                    'name': 'tm3.example.com.dkim.example.net',
                    'deleted_record_ids': [],
                },
            ],
            results['records'],
        )

    @override_settings(
        HOSTED_DKIM_CLOUDFLARE_ENABLED=True,
        HOSTED_DKIM_CLOUDFLARE_ZONE_ID='zone-id',
        HOSTED_DKIM_CLOUDFLARE_API_TOKEN='secret',
        HOSTED_DKIM_DOMAIN='dkim.example.net',
        HOSTED_DKIM_SELECTORS=['tm1'],
    )
    @patch('thunderbird_accounts.mail.tasks.sentry_sdk.set_context')
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    def test_retries_with_context_when_cloudflare_delete_fails(self, cloudflare_client_mock, set_sentry_context_mock):
        cloudflare_client_mock.return_value.delete_txt_records.side_effect = RuntimeError('Cloudflare unavailable')

        with self.assertRaises(HostedDkimDeleteRetry) as cm:
            tasks.delete_hosted_dkim_dns_records.run(domain_name='example.com')

        self.assertEqual('example.com', cm.exception.domain)
        self.assertEqual('delete_cloudflare_txt_records', cm.exception.phase)
        self.assertEqual('Cloudflare unavailable', cm.exception.reason)
        self.assertEqual('example.com', cm.exception.context['domain'])
        self.assertEqual('delete_cloudflare_txt_records', cm.exception.context['phase'])
        self.assertEqual('RuntimeError', cm.exception.context['error_type'])
        set_sentry_context_mock.assert_called_once_with('hosted_dkim_delete_retry', cm.exception.context)


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
