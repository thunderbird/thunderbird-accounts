import json
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

_COMMAND_MODULE = 'thunderbird_accounts.authentication.management.commands.update_reserved_words'


class UpdateReservedWordsCommandTests(TestCase):
    def _run_with_fakes(self) -> dict:
        """Run the command with all network fetches mocked; return the written JSON."""

        def fake_fetch_json(url):
            if url.endswith('/index.json'):
                return ['account', 'pop']
            if url.endswith('/admin-list.json'):
                # 'mail' is demoted; 'p0p' is a leet variant of the demoted 'pop'.
                return ['admin', 'support', 'mail', 'p0p']
            if url.endswith('/no-reply-list.json'):
                return ['noreply']
            if '/data/categories/' in url:
                category = url.split('/data/categories/')[1].split('/')[0]
                return [f'slug-{category}']
            raise AssertionError(f'unexpected fetch url: {url}')

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'reserved').mkdir()
            with (
                mock.patch(f'{_COMMAND_MODULE}._fetch_json', side_effect=fake_fetch_json) as fetch_json,
                mock.patch(f'{_COMMAND_MODULE}._fetch_lines', return_value=['about', 'dev']),
                mock.patch(f'{_COMMAND_MODULE}.apps.get_app_config', return_value=mock.Mock(path=tmp)),
            ):
                call_command('update_reserved_words')
                self._fetched_urls = [call.args[0] for call in fetch_json.call_args_list]
                return json.loads((Path(tmp) / 'reserved' / 'generated-words.json').read_text(encoding='utf-8'))

    def test_writes_warning_and_two_sections(self):
        data = self._run_with_fakes()
        self.assertIn('_warning', data)
        self.assertIn('exact', data)
        self.assertIn('affix', data)

    def test_sources_routed_to_correct_sections(self):
        data = self._run_with_fakes()
        exact, affix = set(data['exact']), set(data['affix'])
        # admin-list / no-reply -> affix
        self.assertIn('admin', affix)
        self.assertIn('support', affix)
        self.assertIn('noreply', affix)
        # index / shouldbee / reserved-slugs -> exact
        self.assertIn('account', exact)
        self.assertIn('about', exact)
        self.assertIn('slug-auth', exact)

    def test_demoted_stems_and_variants_move_to_exact(self):
        data = self._run_with_fakes()
        exact, affix = set(data['exact']), set(data['affix'])
        for word in ['mail', 'p0p']:
            self.assertIn(word, exact, word)
            self.assertNotIn(word, affix, word)

    def test_sections_are_disjoint(self):
        data = self._run_with_fakes()
        self.assertEqual(set(data['exact']) & set(data['affix']), set())

    def test_excluded_categories_are_not_fetched(self):
        self._run_with_fakes()
        for excluded in ('country-codes', 'languages', 'profanity'):
            self.assertFalse(any(excluded in url for url in self._fetched_urls), excluded)
