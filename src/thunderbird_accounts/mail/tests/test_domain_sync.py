from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail import tasks
from thunderbird_accounts.mail.domain_sync import DomainSyncCounts, count_domain_sync
from thunderbird_accounts.mail.exceptions import InvalidJMapResponseError
from thunderbird_accounts.mail.models import Domain
from thunderbird_accounts.mail.tests.test_clients.test_jmap import build_admin_client
from thunderbird_accounts.mail.types.jmap import Invocation, JMapResponse


class PagedDomainServer:
    """Answers x:Domain/query and x:Domain/get over a fixed list of names."""

    def __init__(self, names: list[str], total: int | None = None, overlap: bool = False):
        self.domains = [{'id': f'id-{idx}', 'name': name} for idx, name in enumerate(names)]
        self.total = len(names) if total is None else total
        self.overlap = overlap
        self.queries = []

    def request(self, request_data, method='post'):
        query = request_data.method_calls[0].arguments
        self.queries.append(query)
        start = 0 if self.overlap else query['position']
        page = self.domains[start : start + query['limit']]
        return JMapResponse(
            method_responses=[
                Invocation(
                    name='x:Domain/query',
                    arguments={'ids': [domain['id'] for domain in page], 'total': self.total},
                    method_call_id='0',
                ),
                Invocation(name='x:Domain/get', arguments={'list': page}, method_call_id='1'),
            ],
            session_state='state',
        )


class ListDomainNamesTestCase(SimpleTestCase):
    def setUp(self):
        self.mail_client = build_admin_client()
        self.mail_client.preflight_check = MagicMock()
        self.mail_client.account_id = 'admin-account'

    def _serve(self, server):
        self.mail_client.client.request = server.request

    @override_settings(STALWART_DOMAIN_LIST_PAGE_SIZE=2)
    def test_reads_every_page(self):
        server = PagedDomainServer(['a.test', 'b.test', 'c.test', 'd.test', 'e.test'])
        self._serve(server)

        self.assertEqual(
            {'a.test', 'b.test', 'c.test', 'd.test', 'e.test'},
            self.mail_client.list_domain_names(),
        )
        self.assertEqual([0, 2, 4], [query['position'] for query in server.queries])

    @override_settings(STALWART_DOMAIN_LIST_PAGE_SIZE=2)
    def test_every_page_asks_for_the_total_in_a_fixed_order(self):
        server = PagedDomainServer(['a.test', 'b.test', 'c.test'])
        self._serve(server)

        self.mail_client.list_domain_names()

        for query in server.queries:
            self.assertTrue(query['calculateTotal'])
            self.assertEqual([{'property': 'id', 'isAscending': True}], query['sort'])

    def test_no_domains(self):
        self._serve(PagedDomainServer([]))

        self.assertEqual(set(), self.mail_client.list_domain_names())

    @override_settings(STALWART_DOMAIN_LIST_PAGE_SIZE=2)
    def test_overlapping_pages_are_an_error(self):
        self._serve(PagedDomainServer(['a.test', 'b.test', 'c.test', 'd.test'], overlap=True))

        with self.assertRaises(InvalidJMapResponseError):
            self.mail_client.list_domain_names()

    def test_short_listing_is_an_error(self):
        self._serve(PagedDomainServer(['a.test'], total=2))

        with self.assertRaises(InvalidJMapResponseError):
            self.mail_client.list_domain_names()

    def test_method_error_is_an_error(self):
        self.mail_client.client.request = MagicMock(
            return_value=JMapResponse(
                method_responses=[Invocation(name='error', arguments={'type': 'forbidden'}, method_call_id='0')],
                session_state='state',
            )
        )

        with self.assertRaises(InvalidJMapResponseError):
            self.mail_client.list_domain_names()


class DomainSyncTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='user@example.org', email='user@example.org', oidc_id='oidc-1')

    def _domain(self, name: str, status: Domain.DomainStatus):
        return Domain.objects.create(name=name, user=self.user, status=status)


@override_settings(ALLOWED_EMAIL_DOMAINS=['example.org'])
class CountDomainSyncTestCase(DomainSyncTestCase):
    def test_counts_each_status_in_both_systems(self):
        self._domain('verified.test', Domain.DomainStatus.VERIFIED)
        self._domain('pending.test', Domain.DomainStatus.PENDING)
        self._domain('failed.test', Domain.DomainStatus.FAILED)
        self._domain('pending-accounts-only.test', Domain.DomainStatus.PENDING)

        counts = count_domain_sync({'verified.test', 'pending.test', 'failed.test'})

        self.assertEqual(
            DomainSyncCounts(
                accounts=4, stalwart=3, verified=1, pending=1, failed=1, stalwart_only=0, verified_missing=0
            ),
            counts,
        )

    def test_domain_unknown_to_accounts(self):
        self.assertEqual(1, count_domain_sync({'unknown.test'}).stalwart_only)

    def test_service_domains_are_not_stalwart_only(self):
        self.assertEqual(0, count_domain_sync({'example.org'}).stalwart_only)

    def test_verified_domain_missing_from_stalwart(self):
        self._domain('verified.test', Domain.DomainStatus.VERIFIED)

        self.assertEqual(1, count_domain_sync(set()).verified_missing)

    def test_unicode_and_punycode_names_match(self):
        self._domain('bücher.test', Domain.DomainStatus.VERIFIED)

        counts = count_domain_sync({'xn--bcher-kva.test'})

        self.assertEqual((1, 0, 0), (counts.verified, counts.stalwart_only, counts.verified_missing))


class ReportDomainSyncTestCase(DomainSyncTestCase):
    @override_settings(STALWART_ADMIN_API_USE_JMAP=True, ALLOWED_EMAIL_DOMAINS=['example.org'])
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    def test_logs_counts_without_domain_names(self, mail_client_mock):
        self._domain('verified.test', Domain.DomainStatus.VERIFIED)
        mail_client_mock.return_value.list_domain_names.return_value = {'verified.test', 'unknown.test'}

        with self.assertLogs(level='INFO') as logs:
            result = tasks.report_domain_sync.run()

        self.assertIn(
            '[report_domain_sync] accounts=1 stalwart=2 verified=1 pending=0 failed=0 '
            'stalwart_only=1 verified_missing=0',
            logs.output[0],
        )
        self.assertNotIn('.test', ''.join(logs.output))
        self.assertEqual('success', result['task_status'])
        self.assertEqual(1, result['stalwart_only'])

    @override_settings(STALWART_ADMIN_API_USE_JMAP=True)
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    def test_failed_listing_reports_nothing(self, mail_client_mock):
        mail_client_mock.return_value.list_domain_names.side_effect = requests.ConnectionError('down')

        with self.assertNoLogs(level='INFO'), self.assertRaises(requests.ConnectionError):
            tasks.report_domain_sync.run()

    @override_settings(STALWART_ADMIN_API_USE_JMAP=False)
    @patch('thunderbird_accounts.mail.tasks.MailClient')
    def test_skipped_without_jmap(self, mail_client_mock):
        self.assertEqual('skipped', tasks.report_domain_sync.run()['task_status'])
        mail_client_mock.assert_not_called()
