import json
from unittest.mock import patch, Mock, call

from django.conf import settings
from django.http import JsonResponse
from django.test import TestCase, override_settings, RequestFactory
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail import tasks
from thunderbird_accounts.mail.exceptions import DomainNotFoundError
from thunderbird_accounts.mail.models import Domain
from thunderbird_accounts.mail.views import create_custom_domain
from thunderbird_accounts.subscription.models import Plan, Subscription

MIGRATED = True
NOT_MIGRATED = False

HOSTED_DKIM_SETTINGS = dict(
    HOSTED_DKIM_CLOUDFLARE_ENABLED=True,
    HOSTED_DKIM_CLOUDFLARE_ZONE_ID='zone-id',
    HOSTED_DKIM_CLOUDFLARE_API_TOKEN='secret',
    HOSTED_DKIM_DOMAIN='dkim.example.net',
    HOSTED_DKIM_SELECTORS=['tm1', 'tm2'],
)


class OnboardCustomDomainEndToEndTestCase(TestCase):
    """Exercises the full custom-domain onboarding pipeline end to end:

        A) Stalwart domain principal creation — only for a migrated user.
            - SEE `test_onboarding_when_migrated`'s `create_domain.assert_called_once_with(...)`
              vs. `test_onboarding_when_not_migrated`'s `create_domain.assert_not_called()`.
        B) Stalwart DKIM signature creation — for every user, migrated or not.
            - SEE `mock_view_client.create_dkim.assert_called_once_with` assertion in both tests.
        C) Publishing the DKIM public key as a Cloudflare TXT record — for every user.
            - SEE `mock_cloudflare_client_cls.return_value.upsert_txt_record` assertion in
              `_assert_dkim_published_to_cloudflare`, shared by both tests.

    """

    def setUp(self):
        self.request_factory = RequestFactory()
        self.plan = Plan.objects.create(name='Test Plan', mail_domain_count=10)
        self.url = reverse('add_custom_domain')

    def _make_user(self, username: str) -> User:
        user = User.objects.create(username=username, oidc_id=username, plan=self.plan)
        Subscription.objects.create(user=user, status=Subscription.StatusValues.ACTIVE)
        return user

    def _configure_stalwart_mocks(
        self, mock_view_mail_client_cls: Mock, mock_task_mail_client_cls: Mock, domain_name: str
    ) -> tuple[Mock, Mock]:
        """Wires up the two `MailClient` mocks (view-side and task-side) for a domain that
        doesn't exist yet in Stalwart."""
        mock_view_client = Mock()
        mock_view_client.get_domain.side_effect = DomainNotFoundError(domain_name)
        mock_view_mail_client_cls.return_value = mock_view_client

        # What Stalwart would report back for the signature the view's create_dkim call (above)
        # just told it to create. This feeds dkim.py::build_hosted_dkim_txt_records, which turns
        # it into the Cloudflare TXT record content asserted on by _assert_dkim_published_to_cloudflare.
        mock_task_client = Mock()
        mock_task_client.get_dkim_dns_records.return_value = [
            {
                'type': 'TXT',
                'name': f'tm1._domainkey.{domain_name}.',
                'content': 'v=DKIM1; k=rsa; p=fake-rsa-public-key',
            },
            {
                'type': 'TXT',
                'name': f'tm2._domainkey.{domain_name}.',
                'content': 'v=DKIM1; k=ed25519; p=fake-ed25519-public-key',
            },
        ]
        mock_task_mail_client_cls.return_value = mock_task_client

        return mock_view_client, mock_task_client

    def _post_create_custom_domain(self, domain_name: str, user: User) -> tuple[JsonResponse, Mock]:
        """Runs the real, synchronous view code. Covers A (if migrated) and B."""
        request = self.request_factory.post(
            self.url,
            data=json.dumps({'domain-name': domain_name}),
            content_type='application/json',
        )
        request.user = user

        with patch('thunderbird_accounts.mail.views.mail_tasks.publish_hosted_dkim_dns_records.delay') as mock_delay:
            response = create_custom_domain(request)

        return response, mock_delay

    def _assert_dkim_published_to_cloudflare(self, mock_cloudflare_client_cls: Mock, domain_name: str) -> None:
        """Runs the real task function in-process (normally async on a worker) and asserts both
        DKIM public keys were published as Cloudflare TXT records. Covers C."""
        task_result = tasks.publish_hosted_dkim_dns_records.run(domain_name=domain_name)

        self.assertEqual(task_result['task_status'], 'success')
        self.assertFalse(task_result['skipped'])

        mock_cloudflare_client_cls.return_value.upsert_txt_record.assert_has_calls(
            [
                call(f'tm1.{domain_name}.dkim.example.net', 'v=DKIM1; k=rsa; p=fake-rsa-public-key'),
                call(f'tm2.{domain_name}.dkim.example.net', 'v=DKIM1; k=ed25519; p=fake-ed25519-public-key'),
            ]
        )

    @override_settings(STALWART_ADMIN_API_USE_JMAP=MIGRATED, **HOSTED_DKIM_SETTINGS)
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_onboarding_when_migrated(
        self, mock_view_mail_client_cls, mock_task_mail_client_cls, mock_cloudflare_client_cls
    ):
        domain_name = 'migrated.example.com'
        user = self._make_user(f'test-migrated@{settings.PRIMARY_EMAIL_DOMAIN}')
        mock_view_client, _ = self._configure_stalwart_mocks(
            mock_view_mail_client_cls, mock_task_mail_client_cls, domain_name
        )

        response, mock_delay = self._post_create_custom_domain(domain_name, user)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content.decode())['success'])

        # A: the Stalwart domain principal was created, since this user is migrated.
        mock_view_client.create_domain.assert_called_once_with(domain_name, is_enabled=False)

        # B: the Stalwart DKIM signature was created for that domain.
        mock_view_client.create_dkim.assert_called_once_with(domain_name)

        # The domain was also recorded locally via Django's ORM, same as production.
        self.assertTrue(Domain.objects.filter(name=domain_name, user=user).exists())

        # In production this becomes an async Celery job; here we just confirm it was queued with
        # the right domain before running that same task function inline below.
        mock_delay.assert_called_once_with(domain_name)

        self._assert_dkim_published_to_cloudflare(mock_cloudflare_client_cls, domain_name)

    @override_settings(STALWART_ADMIN_API_USE_JMAP=NOT_MIGRATED, **HOSTED_DKIM_SETTINGS)
    @patch('thunderbird_accounts.mail.tasks.CloudflareDNSClient')
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    @patch('thunderbird_accounts.mail.views.MailClient')
    def test_onboarding_when_not_migrated(
        self, mock_view_mail_client_cls, mock_task_mail_client_cls, mock_cloudflare_client_cls
    ):
        domain_name = 'unmigrated.example.com'
        user = self._make_user(f'test-unmigrated@{settings.PRIMARY_EMAIL_DOMAIN}')
        mock_view_client, _ = self._configure_stalwart_mocks(
            mock_view_mail_client_cls, mock_task_mail_client_cls, domain_name
        )

        response, mock_delay = self._post_create_custom_domain(domain_name, user)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content.decode())['success'])

        # A: the Stalwart domain principal is left for `verify_custom_domain` to create instead,
        # since this user is not migrated.
        mock_view_client.create_domain.assert_not_called()

        # B: the Stalwart DKIM signature was still created for that domain.
        mock_view_client.create_dkim.assert_called_once_with(domain_name)

        # The domain was also recorded locally via Django's ORM, same as production.
        self.assertTrue(Domain.objects.filter(name=domain_name, user=user).exists())

        # In production this becomes an async Celery job; here we just confirm it was queued with
        # the right domain before running that same task function inline below.
        mock_delay.assert_called_once_with(domain_name)

        self._assert_dkim_published_to_cloudflare(mock_cloudflare_client_cls, domain_name)
