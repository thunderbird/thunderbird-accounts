import os
import uuid
from unittest import expectedFailure, skipUnless

import requests
from django.test import SimpleTestCase

from thunderbird_accounts.mail.clients.mail_client_legacy import MailClientLegacy


@skipUnless(os.getenv('STALWART_LEGACY_INTEGRATION') == '1', 'Needs a running legacy Stalwart server')
class DeleteDkimStalwartLegacyTestCase(SimpleTestCase):
    evidence = []

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if path := os.getenv('STALWART_EVIDENCE_FILE'):
            with open(path, 'w') as fh:
                fh.write('\n\n'.join(cls.evidence) + '\n')

    def setUp(self):
        self.mail_client = MailClientLegacy()
        self.token = uuid.uuid4().hex[:8]
        self.addCleanup(self._delete_test_signers)

    def _create_signers(self, *domains):
        for domain in domains:
            self.mail_client.create_dkim(domain)

    def _signer_domains(self):
        response = requests.get(
            f'{self.mail_client.api_url}/settings/list',
            params={'prefix': 'signature'},
            headers=self.mail_client.authorized_headers,
        )
        response.raise_for_status()
        settings = response.json()['data']['items']
        return sorted({value for key, value in settings.items() if key.endswith('.domain') and self.token in value})

    def _delete_test_signers(self):
        response = requests.post(
            f'{self.mail_client.api_url}/settings',
            json=[{'type': 'clear', 'prefix': 'signature.', 'filter': self.token}],
            headers=self.mail_client.authorized_headers,
        )
        response.raise_for_status()

    def _delete_dkim(self, domain):
        self.deleted = domain
        self.signers_before = self._signer_domains()
        self.mail_client.delete_dkim(domain)

    def _assert_signers_left(self, expected):
        actual = self._signer_domains()
        self.evidence.append(self._describe(expected, actual))
        self.assertEqual(expected, actual)

    def _describe(self, expected, actual):
        wrongly_deleted = [domain for domain in expected if domain not in actual]
        if actual == expected:
            result = f"As expected, only {self.deleted}'s signers were deleted."
        elif wrongly_deleted:
            result = (
                f'delete_dkim also deleted the signers of {", ".join(wrongly_deleted)}, '
                f"but only {self.deleted}'s signers should have been deleted. "
                "This is evidence of the #1270 bug: delete_dkim deletes other domains' DKIM signers."
            )
        else:
            result = 'The signers left differ from what was expected.'

        return '\n'.join(
            [
                self._testMethodName,
                f'  Called:   delete_dkim({self.deleted!r})',
                f'  Before:   {", ".join(self.signers_before)}',
                f'  Expected: {", ".join(expected) or "(none)"}',
                f'  Actual:   {", ".join(actual) or "(none)"}',
                f'  Result:   {result}',
            ]
        )

    @expectedFailure
    def test_keeps_signers_of_shorter_domain(self):
        kept = f'thundermail{self.token}.com'
        deleted = f'thundermail{self.token}.com.au'
        self._create_signers(kept, deleted)

        self._delete_dkim(deleted)

        self._assert_signers_left([kept])

    @expectedFailure
    def test_keeps_signers_of_containing_domain(self):
        kept = f'thunder{self.token}mail.com'
        deleted = f'{self.token}mail.com'
        self._create_signers(kept, deleted)

        self._delete_dkim(deleted)

        self._assert_signers_left([kept])

    @expectedFailure
    def test_keeps_signers_of_other_customers(self):
        kept = [f'example{self.token}.com.au', f'myexample{self.token}.com']
        deleted = f'example{self.token}.com'
        self._create_signers(deleted, *kept)

        self._delete_dkim(deleted)

        self._assert_signers_left(kept)

    def test_keeps_signers_of_unrelated_domain(self):
        kept = f'thundermail{self.token}.com'
        deleted = f'customdomain{self.token}.org'
        self._create_signers(kept, deleted)

        self._delete_dkim(deleted)

        self._assert_signers_left([kept])
