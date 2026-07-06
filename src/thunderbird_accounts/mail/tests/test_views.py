import datetime
from thunderbird_accounts.mail.exceptions import DomainNotFoundError
from django.utils.crypto import get_random_string
from thunderbird_accounts.subscription.models import Plan, Subscription
import json
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings, RequestFactory
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.core.tests.utils import oidc_force_login
from thunderbird_accounts.mail.clients import DomainVerificationErrors, StaleDNSRecordCode
from thunderbird_accounts.mail.models import Account, Domain, Email
from thunderbird_accounts.mail.views import get_dns_records, remove_custom_domain


class AppPasswordApiTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        self.primary_email = f'test@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.account = Account.objects.create(name=self.primary_email, user=self.user)
        Email.objects.create(address=self.primary_email, type=Email.EmailType.PRIMARY, account=self.account)
        self.subscription = Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.client.force_login(self.user)
        self.url = reverse('api_app_password_set')

    @patch('thunderbird_accounts.mail.views.utils.save_app_password')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success(self, mock_mail_client_cls, mock_save_app_password):
        existing_app_password = f'$app${self.primary_email}$hashed-password'
        new_hash = f'$app${self.primary_email}$new-hashed-password'

        mock_instance = Mock()
        mock_instance.get_account.return_value = {'secrets': [existing_app_password]}
        mock_mail_client_cls.return_value = mock_instance
        mock_save_app_password.return_value = new_hash

        response = self.client.post(
            self.url,
            data=json.dumps({'name': self.primary_email, 'password': 'new-password'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content.decode())['success'])
        mock_instance.get_account.assert_called_once_with(self.primary_email)
        mock_instance.delete_app_password.assert_called_once_with(self.primary_email, existing_app_password)
        mock_save_app_password.assert_called_once_with(self.primary_email, 'new-password')
        mock_instance.save_app_password.assert_called_once_with(self.primary_email, new_hash)

    def test_name_and_password_are_required(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'name': self.primary_email}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content.decode())['success'])

    @patch('thunderbird_accounts.mail.views.utils.save_app_password')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_requires_active_subscription(self, mock_mail_client_cls, mock_save_app_password):
        self.subscription.status = Subscription.StatusValues.CANCELED
        self.subscription.save()

        response = self.client.post(
            self.url,
            data=json.dumps({'name': self.primary_email, 'password': 'new-password'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(json.loads(response.content.decode())['success'])
        mock_mail_client_cls.assert_not_called()
        mock_save_app_password.assert_not_called()


class DisplayNameApiTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.primary_email = f'test@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.account = Account.objects.create(name=self.primary_email, user=self.user)
        Email.objects.create(address=self.primary_email, type=Email.EmailType.PRIMARY, account=self.account)
        self.client.force_login(self.user)
        self.url = reverse('api_display_name_set')

    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success(self, mock_mail_client_cls):
        mock_instance = Mock()
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'display-name': 'New Name'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content.decode())['success'])
        mock_instance.update_individual.assert_called_once_with(self.primary_email, full_name='New Name')

    def test_display_name_is_required(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'display-name': ''}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content.decode())['success'])


class ActiveSubscriptionRequiredMailViewsTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        oidc_force_login(self.client, self.user)

    def test_mail_management_views_require_active_subscription(self):
        cases = [
            ('api_display_name_set', 'post', {'display-name': 'New Name'}),
            ('add_custom_domain', 'post', {'domain-name': 'example.com'}),
            ('get_dns_records', 'get', {'domain-name': 'example.com'}),
            ('verify_custom_domain', 'post', {'domain-name': 'example.com'}),
            ('remove_custom_domain', 'delete', {'domain-name': 'example.com'}),
            ('add_email_alias', 'post', {'email-alias': 'buddy', 'domain': settings.PRIMARY_EMAIL_DOMAIN}),
            ('remove_email_alias', 'delete', {'email-alias': f'buddy@{settings.PRIMARY_EMAIL_DOMAIN}'}),
        ]
        if settings.AUTH_SCHEME == 'oidc':
            cases.append(('jmap-test', 'get', {}))

        for url_name, method, data in cases:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                if method == 'get':
                    response = self.client.get(url, data=data, HTTP_ACCEPT='application/json')
                else:
                    response = getattr(self.client, method)(
                        url,
                        data=json.dumps(data),
                        content_type='application/json',
                        HTTP_ACCEPT='application/json',
                    )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.json(),
                    {'success': False, 'error': 'An active subscription is required.'},
                )


@override_settings(HOSTED_DKIM_DOMAIN='dkim.example.net', HOSTED_DKIM_SELECTORS=['tm1', 'tm2', 'tm3'])
class CustomDomainDNSRecordsTestCase(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.domain = Domain.objects.create(name='example.com', user=self.user)
        self.url = reverse('get_dns_records')

    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_returns_expected_dns_records_without_verification(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim_dns_records,
    ):
        dkim_records = [
            {
                'type': 'CNAME',
                'name': 'tm1._domainkey.example.com.',
                'content': 'tm1.example.com.dkim.example.net.',
                'priority': '-',
            },
            {
                'type': 'CNAME',
                'name': 'tm2._domainkey.example.com.',
                'content': 'tm2.example.com.dkim.example.net.',
                'priority': '-',
            },
            {
                'type': 'CNAME',
                'name': 'tm3._domainkey.example.com.',
                'content': 'tm3.example.com.dkim.example.net.',
                'priority': '-',
            },
        ]
        mock_instance = Mock()
        dns_records = [
            {'type': 'MX', 'name': '@', 'content': 'mail.example.net', 'priority': '10'},
            *dkim_records,
        ]
        mock_instance.build_expected_dns_records.return_value = dns_records
        mock_mail_client_cls.return_value = mock_instance

        request = self.request_factory.get(self.url, {'domain-name': self.domain.name})
        request.user = self.user

        response = get_dns_records(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertTrue(data['success'])
        self.assertEqual(dns_records, data['dns_records'])
        self.assertEqual(dkim_records, data['dkim_cname_records'])
        self.assertEqual([], data['critical_errors'])
        self.assertEqual([], data['warnings'])
        self.assertEqual([], data['stale_dns_records'])
        mock_instance.build_expected_dns_records.assert_called_once_with(self.domain.name)
        mock_instance.ensure_dkim.assert_not_called()
        mock_instance.check_domain_dns.assert_not_called()
        mock_instance.create_dkim.assert_not_called()
        mock_check_stale_dns_records.assert_not_called()
        mock_publish_hosted_dkim_dns_records.assert_not_called()


class VerifyCustomDomainTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.domain = Domain.objects.create(name='example.com', user=self.user)
        self.client.force_login(self.user)
        self.url = reverse('verify_custom_domain')

    @override_settings(CUSTOM_DOMAINS_DO_VERIFY=True)
    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success_does_not_activate_pending_dkim_by_default(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim,
    ):
        mock_instance = Mock()
        mock_instance.check_domain_dns.return_value = {
            'is_verified': True,
            'critical_errors': [],
            'warnings': [],
            'dns_records': [],
        }
        mock_instance.create_domain.return_value = 'domain-id'
        mock_instance.get_domain.side_effect = DomainNotFoundError(
            self.domain.name
        )  # Make sure we don't actually have a domain here
        mock_check_stale_dns_records.return_value = []
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertTrue(data['success'])
        mock_instance.check_domain_dns.assert_called_once_with(self.domain.name)
        mock_check_stale_dns_records.assert_called_once_with(self.domain.name)
        mock_instance.create_domain.assert_called_once_with(self.domain.name)
        mock_instance.get_domain.assert_called_once_with(self.domain.name)
        mock_instance.ensure_dkim.assert_called_once_with(self.domain.name)
        mock_instance.create_dkim.assert_not_called()
        mock_publish_hosted_dkim.assert_called_once_with(self.domain.name)
        mock_instance.activate_pending_dkim_signatures.assert_not_called()

        self.domain.refresh_from_db()
        self.assertEqual(Domain.DomainStatus.VERIFIED, self.domain.status)
        self.assertEqual('domain-id', self.domain.stalwart_id)

    @override_settings(CUSTOM_DOMAINS_DO_VERIFY=True)
    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_reverification_of_ok_domain_is_success(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim,
    ):
        stalwart_id = self.domain.stalwart_id
        self.domain.stalwart_id = stalwart_id
        self.domain.status = Domain.DomainStatus.VERIFIED
        self.domain.stalwart_created_at = datetime.datetime.now(datetime.UTC)
        self.domain.save()

        mock_instance = Mock()
        mock_instance.check_domain_dns.return_value = {
            'is_verified': True,
            'critical_errors': [],
            'warnings': [],
            'dns_records': [],
        }
        mock_instance.create_domain.return_value = None
        mock_instance.get_domain.side_effect = {'id': stalwart_id}
        mock_check_stale_dns_records.return_value = []
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content.decode())
        self.assertTrue(data['success'])
        mock_instance.check_domain_dns.assert_called_once_with(self.domain.name)
        mock_check_stale_dns_records.assert_called_once_with(self.domain.name)
        mock_instance.create_domain.assert_not_called()
        mock_instance.get_domain.assert_called_once_with(self.domain.name)

        mock_instance.ensure_dkim.assert_not_called()
        mock_instance.create_dkim.assert_not_called()
        mock_publish_hosted_dkim.assert_not_called()
        mock_instance.activate_pending_dkim_signatures.assert_not_called()

        self.domain.refresh_from_db()
        self.assertEqual(Domain.DomainStatus.VERIFIED, self.domain.status)
        self.assertEqual(stalwart_id, self.domain.stalwart_id)

    @override_settings(CUSTOM_DOMAINS_DO_VERIFY=True)
    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_reverification_of_bad_domain_is_success(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim,
    ):
        """This test-case is a reverification of a VERIFIED domain that does not have a Stalwart entry"""
        stalwart_id = self.domain.stalwart_id
        self.domain.stalwart_id = stalwart_id
        self.domain.status = Domain.DomainStatus.VERIFIED
        self.domain.stalwart_created_at = datetime.datetime.now(datetime.UTC)
        self.domain.save()

        mock_instance = Mock()
        mock_instance.check_domain_dns.return_value = {
            'is_verified': True,
            'critical_errors': [],
            'warnings': [],
            'dns_records': [],
        }
        mock_instance.create_domain.return_value = stalwart_id
        mock_instance.get_domain.side_effect = DomainNotFoundError(self.domain.name)
        mock_check_stale_dns_records.return_value = []
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content.decode())
        self.assertTrue(data['success'])
        mock_instance.check_domain_dns.assert_called_once_with(self.domain.name)
        mock_check_stale_dns_records.assert_called_once_with(self.domain.name)
        mock_instance.create_domain.assert_called_once_with(self.domain.name)
        mock_instance.get_domain.assert_called_once_with(self.domain.name)

        mock_instance.ensure_dkim.assert_called_once_with(self.domain.name)
        mock_instance.create_dkim.assert_not_called()
        mock_publish_hosted_dkim.assert_called_once_with(self.domain.name)
        mock_instance.activate_pending_dkim_signatures.assert_not_called()

        self.domain.refresh_from_db()
        self.assertEqual(Domain.DomainStatus.VERIFIED, self.domain.status)
        self.assertEqual(stalwart_id, self.domain.stalwart_id)

    @override_settings(CUSTOM_DOMAINS_DO_VERIFY=True)
    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_reverification_of_unverified_domain_is_success(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim,
    ):
        """This test-case is a reverification of a VERIFIED domain that does not have a Stalwart entry"""
        stalwart_id = self.domain.stalwart_id
        self.domain.stalwart_id = stalwart_id
        self.domain.status = Domain.DomainStatus.FAILED
        self.domain.stalwart_created_at = datetime.datetime.now(datetime.UTC)
        self.domain.save()

        mock_instance = Mock()
        mock_instance.check_domain_dns.return_value = {
            'is_verified': True,
            'critical_errors': [],
            'warnings': [],
            'dns_records': [],
        }
        mock_instance.create_domain.return_value = None
        mock_instance.get_domain.return_value = {'id': stalwart_id}
        mock_check_stale_dns_records.return_value = []
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content.decode())
        self.assertTrue(data['success'])
        mock_instance.check_domain_dns.assert_called_once_with(self.domain.name)
        mock_check_stale_dns_records.assert_called_once_with(self.domain.name)
        mock_instance.create_domain.assert_not_called()
        mock_instance.get_domain.assert_called_once_with(self.domain.name)

        mock_instance.ensure_dkim.assert_called_once_with(self.domain.name)
        mock_instance.create_dkim.assert_not_called()
        mock_publish_hosted_dkim.assert_called_once_with(self.domain.name)
        mock_instance.activate_pending_dkim_signatures.assert_not_called()

        self.domain.refresh_from_db()
        self.assertEqual(Domain.DomainStatus.VERIFIED, self.domain.status)
        self.assertEqual(stalwart_id, self.domain.stalwart_id)

    @override_settings(CUSTOM_DOMAINS_DO_VERIFY=True)
    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_autodiscover_record_is_critical_error(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim,
    ):
        mock_instance = Mock()
        mock_instance.check_domain_dns.return_value = {
            'is_verified': True,
            'critical_errors': [],
            'warnings': [],
            'dns_records': [],
        }
        mock_mail_client_cls.return_value = mock_instance
        mock_check_stale_dns_records.return_value = [
            {
                'code': StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value,
                'type': 'A',
                'name': f'autodiscover.{self.domain.name}',
                'existing_values': ['203.0.113.10'],
            }
        ]

        response = self.client.post(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertFalse(data['success'])
        self.assertIn(DomainVerificationErrors.AUTODISCOVER_RECORD_FOUND.value, data['critical_errors'])
        self.assertEqual(mock_check_stale_dns_records.return_value, data['stale_dns_records'])
        mock_instance.create_domain.assert_not_called()
        mock_instance.ensure_dkim.assert_not_called()
        mock_publish_hosted_dkim.assert_not_called()

        self.domain.refresh_from_db()
        self.assertEqual(Domain.DomainStatus.FAILED, self.domain.status)

    @override_settings(CUSTOM_DOMAINS_DO_VERIFY=True)
    @patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.check_stale_dns_records')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_autodiscover_srv_record_is_critical_error(
        self,
        mock_mail_client_cls,
        mock_check_stale_dns_records,
        mock_publish_hosted_dkim,
    ):
        mock_instance = Mock()
        mock_instance.check_domain_dns.return_value = {
            'is_verified': True,
            'critical_errors': [],
            'warnings': [],
            'dns_records': [],
        }
        mock_mail_client_cls.return_value = mock_instance
        mock_check_stale_dns_records.return_value = [
            {
                'code': StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value,
                'type': 'SRV',
                'name': f'_autodiscover._tcp.{self.domain.name}',
                'existing_values': ['0 0 443 cpanelemaildiscovery.cpanel.net'],
            }
        ]

        response = self.client.post(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertFalse(data['success'])
        self.assertIn(DomainVerificationErrors.AUTODISCOVER_SRV_RECORD_FOUND.value, data['critical_errors'])
        self.assertEqual(mock_check_stale_dns_records.return_value, data['stale_dns_records'])
        mock_instance.create_domain.assert_not_called()
        mock_instance.ensure_dkim.assert_not_called()
        mock_publish_hosted_dkim.assert_not_called()

        self.domain.refresh_from_db()
        self.assertEqual(Domain.DomainStatus.FAILED, self.domain.status)


class RemoveCustomDomainTestCase(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.account = Account.objects.create(name=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)
        self.domain = Domain.objects.create(
            name='example.com',
            user=self.user,
            stalwart_id='domain-id',
            status=Domain.DomainStatus.VERIFIED,
        )
        self.url = reverse('remove_custom_domain')

    def _delete_domain(self):
        request = self.request_factory.delete(
            self.url,
            data=json.dumps({'domain-name': self.domain.name}),
            content_type='application/json',
        )
        request.user = self.user
        return remove_custom_domain(request)

    @patch('thunderbird_accounts.mail.views.mail_tasks.delete_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success_deletes_stalwart_dkim_cloudflare_records_and_local_domain(
        self,
        mock_mail_client_cls,
        mock_delete_hosted_dkim_dns_records,
    ):
        mock_instance = Mock()
        mock_mail_client_cls.return_value = mock_instance

        response = self._delete_domain()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {'success': True})
        mock_instance.delete_domain.assert_called_once_with(self.domain.name)
        mock_instance.delete_dkim.assert_called_once_with(self.domain.name)
        mock_delete_hosted_dkim_dns_records.assert_called_once_with(self.domain.name)
        self.assertFalse(Domain.objects.filter(name=self.domain.name).exists())

    @patch('thunderbird_accounts.mail.views.mail_tasks.delete_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_pending_domain_still_deletes_dkim_and_cloudflare_records(
        self,
        mock_mail_client_cls,
        mock_delete_hosted_dkim_dns_records,
    ):
        self.domain.stalwart_id = None
        self.domain.status = Domain.DomainStatus.PENDING
        self.domain.save()
        mock_instance = Mock()
        mock_mail_client_cls.return_value = mock_instance

        response = self._delete_domain()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {'success': True})
        mock_instance.delete_domain.assert_not_called()
        mock_instance.delete_dkim.assert_called_once_with(self.domain.name)
        mock_delete_hosted_dkim_dns_records.assert_called_once_with(self.domain.name)
        self.assertFalse(Domain.objects.filter(name=self.domain.name).exists())

    @patch('thunderbird_accounts.mail.views.mail_tasks.delete_hosted_dkim_dns_records.delay')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_domain_with_alias_cannot_be_removed(
        self,
        mock_mail_client_cls,
        mock_delete_hosted_dkim_dns_records,
    ):
        Email.objects.create(address=f'alias@{self.domain.name}', type=Email.EmailType.ALIAS, account=self.account)

        response = self._delete_domain()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content.decode())['success'])
        mock_mail_client_cls.assert_not_called()
        mock_delete_hosted_dkim_dns_records.assert_not_called()
        self.assertTrue(Domain.objects.filter(name=self.domain.name).exists())


class AddEmailAliasTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.plan = Plan.objects.create(name='Test Plan', mail_address_count=5)
        self.user = User.objects.create(
            username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234', plan=self.plan
        )
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.account = Account.objects.create(name=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)
        self.client.force_login(self.user)

    def test_success(self):
        email_alias_url = reverse('add_email_alias')

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

    def test_rejects_alias_with_plus_symbol(self):
        email_alias_url = reverse('add_email_alias')

        response = self.client.post(
            email_alias_url,
            data={'email-alias': 'buddy+tag', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content.decode()),
            {'success': False, 'error': _('The + symbol is not allowed.')},
        )

    def test_success_catch_all(self):
        email_alias_url = reverse('add_email_alias')
        domain = Domain.objects.create(
            name='customdomain.com',
            user=self.user,
            status=Domain.DomainStatus.VERIFIED,
        )

        for alias in ['', '*']:
            with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
                instance = Mock()
                mock.save_email_addresses = instance
                response = self.client.post(
                    email_alias_url,
                    data={'email-alias': alias, 'domain': domain.name},
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.content.decode()), {'success': True})

            # Remove all emails so we can try the next alias
            Email.objects.all().delete()

    def test_failed_catch_all_in_use(self):
        email_alias_url = reverse('add_email_alias')
        domain = Domain.objects.create(
            name='customdomain.com',
            user=self.user,
            status=Domain.DomainStatus.VERIFIED,
        )

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': '*', 'domain': domain.name},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

            response = self.client.post(
                email_alias_url,
                data={'email-alias': '*', 'domain': domain.name},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                json.loads(response.content.decode()),
                {'success': False, 'error': _('You cannot use this email address.')},
            )

    def test_failed_catch_all_with_shared_domain(self):
        email_alias_url = reverse('add_email_alias')

        for alias in ['', '*']:
            with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
                instance = Mock()
                mock.save_email_addresses = instance
                response = self.client.post(
                    email_alias_url,
                    data={'email-alias': '*', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    json.loads(response.content.decode()),
                    {'error': 'Email alias must be at least 3 characters long.', 'success': False},
                )

            # Remove all emails so we can try the next alias
            Email.objects.all().delete()

    def test_too_many_aliases(self):
        email_alias_url = reverse('add_email_alias')

        # Decrease the limit to 1 alias for shared domains
        self.plan.mail_address_count = 1
        self.plan.save()

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy2', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                json.loads(response.content.decode()), {'error': 'You cannot create anymore aliases.', 'success': False}
            )

    def test_custom_domains_dont_affect_limit(self):
        email_alias_url = reverse('add_email_alias')

        domain = Domain.objects.create(
            name='customdomain.com',
            user=self.user,
            status=Domain.DomainStatus.VERIFIED,
        )

        # Decrease the limit to 1 alias for shared domains
        self.plan.mail_address_count = 1
        self.plan.save()

        # Test the following new aliases:
        # 1. buddy@customdomain.com (no limit)
        # 2. buddy@example.com (hits the limit)
        # 3. buddy2@customdomain.com (no limit, would error out if custom domains counted)
        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy', 'domain': domain.name},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy2', 'domain': domain.name},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

    def test_reserved(self):
        email_alias_url = reverse('add_email_alias')

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'admin', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                json.loads(response.content.decode()),
                {'success': False, 'error': _('You cannot use this email address.')},
            )

    def test_reserved_with_custom_domain(self):
        """Ensure that creating an email alias with a reserved word for a custom domain is ok."""
        email_alias_url = reverse('add_email_alias')
        domain = Domain.objects.create(
            name='customdomain.com',
            user=self.user,
            status=Domain.DomainStatus.VERIFIED,
        )

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'admin', 'domain': domain.name},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

    def test_already_used_alias(self):
        """Ensure that creating an email alias that is already in-use will error out."""
        email_alias_url = reverse('add_email_alias')

        Email(address=f'cool_dude_99@{settings.PRIMARY_EMAIL_DOMAIN}').save()

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'cool_dude_99', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                json.loads(response.content.decode()),
                {'success': False, 'error': _('You cannot use this email address.')},
            )

    def test_already_used_alias_case_sensitive(self):
        """Ensure that creating an email alias with differing case that is already in-use will error out."""
        email_alias_url = reverse('add_email_alias')

        Email(address=f'cool_dude_00@{settings.PRIMARY_EMAIL_DOMAIN}').save()

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'COOL_dude_00', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                json.loads(response.content.decode()),
                {'success': False, 'error': _('You cannot use this email address.')},
            )

    @override_settings(ALLOWED_EMAIL_DOMAINS=['example.org', 'example.com'])
    @override_settings(MIN_CUSTOM_DOMAIN_ALIAS_LENGTH=3)
    def test_allowed_domain_alias_too_short(self):
        """Test that email aliases shorter than 3 characters are rejected for ALLOWED_EMAIL_DOMAINS."""
        email_alias_url = reverse('add_email_alias')

        # Test with 1 character
        response = self.client.post(
            email_alias_url,
            data={'email-alias': 'a', 'domain': 'example.org'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content.decode()),
            {'success': False, 'error': _('Email alias must be at least 3 characters long.')},
        )

        # Test with 2 characters
        response = self.client.post(
            email_alias_url,
            data={'email-alias': 'ab', 'domain': 'example.org'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content.decode()),
            {'success': False, 'error': _('Email alias must be at least 3 characters long.')},
        )

    @override_settings(ALLOWED_EMAIL_DOMAINS=['example.org', 'example.com'])
    def test_allowed_domains_alias_too_long(self):
        """Test that email aliases longer than 150 characters are rejected for ALLOWED_EMAIL_DOMAINS."""
        email_alias_url = reverse('add_email_alias')

        random_string = get_random_string(User.USERNAME_MAX_LENGTH + 1)

        response = self.client.post(
            email_alias_url,
            data={'email-alias': random_string, 'domain': 'example.org'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400, msg=response.content.decode())
        self.assertEqual(
            json.loads(response.content.decode()),
            {'success': False, 'error': _('This email is not valid. Try another one.')},
        )

        response = self.client.post(
            email_alias_url,
            data={'email-alias': random_string, 'domain': 'example.org'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400, msg=response.content.decode())
        self.assertEqual(
            json.loads(response.content.decode()),
            {'success': False, 'error': _('This email is not valid. Try another one.')},
        )

    @override_settings(ALLOWED_EMAIL_DOMAINS=['example.org', 'example.com'])
    @override_settings(MIN_CUSTOM_DOMAIN_ALIAS_LENGTH=3)
    def test_allowed_domain_alias_minimum_length(self):
        """Test that email aliases of exactly 3 characters are accepted for ALLOWED_EMAIL_DOMAINS."""
        email_alias_url = reverse('add_email_alias')

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'abc', 'domain': 'example.org'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

    @override_settings(ALLOWED_EMAIL_DOMAINS=['example.org', 'example.com'])
    @override_settings(MIN_CUSTOM_DOMAIN_ALIAS_LENGTH=3)
    def test_custom_domain_alias_short_allowed(self):
        """Test that short email aliases (< 3 chars) are allowed for custom domains (not in ALLOWED_EMAIL_DOMAINS)."""
        email_alias_url = reverse('add_email_alias')
        Domain.objects.create(
            name='customdomain.com',
            user=self.user,
            status=Domain.DomainStatus.VERIFIED,
        )

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            # Test with 1 character - should succeed for custom domain
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'a', 'domain': 'customdomain.com'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

            # Test with 2 characters - should succeed for custom domain
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'ab', 'domain': 'customdomain.com'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

    @override_settings(ALLOWED_EMAIL_DOMAINS=['example.org', 'example.com'])
    @override_settings(MIN_CUSTOM_DOMAIN_ALIAS_LENGTH=2)
    def test_custom_domain_alias_length_minimum_2(self):
        """Test that MIN_CUSTOM_DOMAIN_ALIAS_LENGTH=2 works correctly for both allowed and custom domains."""
        email_alias_url = reverse('add_email_alias')
        Domain.objects.create(
            name='customdomain.com',
            user=self.user,
            status=Domain.DomainStatus.VERIFIED,
        )

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance

            # Test ALLOWED_EMAIL_DOMAINS: 1 character should be rejected
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'a', 'domain': 'example.org'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                json.loads(response.content.decode()),
                {'success': False, 'error': _('Email alias must be at least 3 characters long.')},
            )

            # Test ALLOWED_EMAIL_DOMAINS: 2 characters should be accepted
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'ab', 'domain': 'example.org'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

            # Test custom domain: 1 character should be allowed
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'a', 'domain': 'customdomain.com'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

            # Test custom domain: 2 characters should be allowed
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'ab', 'domain': 'customdomain.com'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})


class AppointmentCalDAVSetupTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(
            username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}',
            oidc_id='1234',
        )
        self.account = Account.objects.create(name=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)

        # Create primary email so stalwart_primary_email property works
        Email.objects.create(
            address=f'test@{settings.PRIMARY_EMAIL_DOMAIN}',
            type=Email.EmailType.PRIMARY,
            account=self.account,
        )

        self.user.has_active_subscription = True

        self.url = reverse('appointment_caldav_setup')
        self.access_token = 'test-access-token-123'

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    def test_missing_appointment_secret(self):
        """Test that missing appointment-secret returns 400 error."""
        response = self.client.post(
            self.url,
            data=json.dumps({'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    def test_invalid_appointment_secret(self):
        """Test that invalid appointment-secret returns 400 error."""
        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'wrong-secret', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    def test_missing_oidc_access_token(self):
        """Test that missing oidc-access-token returns 400 error."""
        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='')
    def test_appointment_caldav_secret_not_set(self):
        """Test that 500 is returned when APPOINTMENT_CALDAV_SECRET is not set."""
        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 500)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    def test_oidc_validation_failure(self, mock_backend_cls):
        """Test that 401 is returned when OIDC token validation fails."""
        mock_backend = Mock()
        mock_backend.get_user_from_access_token.side_effect = Exception('Token validation failed')
        mock_backend_cls.return_value = mock_backend

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    def test_user_not_found(self, mock_backend_cls):
        """Test that 404 is returned when user is not found."""
        mock_backend = Mock()
        mock_backend.get_user_from_access_token.return_value = None
        mock_backend_cls.return_value = mock_backend

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    def test_user_without_active_subscription(self, mock_backend_cls):
        """Test that 400 is returned when user does not have an active subscription."""
        self.user.has_active_subscription = False

        mock_backend = Mock()
        mock_backend.get_user_from_access_token.return_value = self.user
        mock_backend_cls.return_value = mock_backend

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.secrets.token_urlsafe')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    @patch('thunderbird_accounts.mail.views.utils.save_app_password')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success_existing_app_password_replaced(
        self, mock_mail_client_cls, mock_save_app_password, mock_backend_cls, mock_token_urlsafe
    ):
        """Test that an existing app password is deleted and replaced with a new one."""
        label = f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}{self.user.stalwart_primary_email}'
        existing_app_password = f'$app${label}$hashed-password'
        new_hash = f'$app${label}$new-hashed-password'

        mock_token_urlsafe.return_value = 'random-base64-password'
        mock_save_app_password.return_value = new_hash

        mock_backend = Mock()
        mock_backend.get_user_from_access_token.return_value = self.user
        mock_backend_cls.return_value = mock_backend

        mock_instance = Mock()
        mock_instance.get_account.return_value = {
            'secrets': [existing_app_password, '$app$other-label$other-hash'],
        }
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertTrue(payload['success'])
        self.assertEqual(payload['app_password'], 'random-base64-password')

        mock_instance.get_account.assert_called_once_with(self.user.stalwart_primary_email)
        mock_instance.delete_app_password.assert_called_once_with(
            self.user.stalwart_primary_email, existing_app_password
        )
        mock_save_app_password.assert_called_once_with(label, 'random-base64-password')
        mock_instance.save_app_password.assert_called_once_with(self.user.stalwart_primary_email, new_hash)

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.secrets.token_urlsafe')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    @patch('thunderbird_accounts.mail.views.utils.save_app_password')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success_new_app_password_created(
        self, mock_mail_client_cls, mock_save_app_password, mock_backend_cls, mock_token_urlsafe
    ):
        """Test successful creation of new app password when no matching one exists."""
        label = f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}{self.user.stalwart_primary_email}'
        new_hash = f'$app${label}$new-hashed-password'

        mock_token_urlsafe.return_value = 'random-base64-password'
        mock_save_app_password.return_value = new_hash

        mock_backend = Mock()
        mock_backend.get_user_from_access_token.return_value = self.user
        mock_backend_cls.return_value = mock_backend

        mock_instance = Mock()
        mock_instance.get_account.return_value = {
            'secrets': ['$app$other-label$other-hash'],
        }
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertTrue(payload['success'])
        self.assertEqual(payload['app_password'], 'random-base64-password')

        mock_instance.get_account.assert_called_once_with(self.user.stalwart_primary_email)
        mock_instance.delete_app_password.assert_not_called()
        mock_save_app_password.assert_called_once_with(label, 'random-base64-password')
        mock_instance.save_app_password.assert_called_once_with(self.user.stalwart_primary_email, new_hash)

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.secrets.token_urlsafe')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    @patch('thunderbird_accounts.mail.views.utils.save_app_password')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_success_no_existing_secrets(
        self, mock_mail_client_cls, mock_save_app_password, mock_backend_cls, mock_token_urlsafe
    ):
        """Test successful creation when user has no existing secrets."""
        label = f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}{self.user.stalwart_primary_email}'
        new_hash = f'$app${label}$new-hashed-password'

        mock_token_urlsafe.return_value = 'random-base64-password'
        mock_save_app_password.return_value = new_hash

        mock_backend = Mock()
        mock_backend.get_user_from_access_token.return_value = self.user
        mock_backend_cls.return_value = mock_backend

        mock_instance = Mock()
        mock_instance.get_account.return_value = {
            'secrets': [],
        }
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertTrue(payload['success'])
        self.assertEqual(payload['app_password'], 'random-base64-password')

        mock_instance.delete_app_password.assert_not_called()
        mock_save_app_password.assert_called_once_with(label, 'random-base64-password')
        mock_instance.save_app_password.assert_called_once_with(self.user.stalwart_primary_email, new_hash)

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    @patch('thunderbird_accounts.mail.views.AccountsOIDCBackend')
    @patch('thunderbird_accounts.mail.views.sentry_sdk.capture_exception')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_exception_handling(self, mock_mail_client_cls, mock_capture_exception, mock_backend_cls):
        """Test that exceptions are caught and return 500 error."""
        mock_backend = Mock()
        mock_backend.get_user_from_access_token.return_value = self.user
        mock_backend_cls.return_value = mock_backend

        mock_instance = Mock()
        mock_instance.get_account.side_effect = Exception('Test exception')
        mock_mail_client_cls.return_value = mock_instance

        response = self.client.post(
            self.url,
            data=json.dumps({'appointment-secret': 'test-secret-123', 'oidc-access-token': self.access_token}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 500)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))
        mock_capture_exception.assert_called_once()

    @override_settings(APPOINTMENT_CALDAV_SECRET='test-secret-123')
    def test_invalid_json_body(self):
        """Test that invalid JSON body returns 400 error."""
        response = self.client.post(
            self.url,
            data='invalid json',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload['success'])
        self.assertEqual(payload['error'], _('An error has occurred while setting up the Appointment CalDAV.'))
