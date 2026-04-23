import json
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.core.tests.utils import oidc_force_login
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.legal.views import _read_legal_content


class LegalDocCleanSlateTestCase(TestCase):
    """Clears seeded LegalDocument rows so each test starts with a known-empty table."""

    def setUp(self):
        super().setUp()
        LegalDocument.objects.all().delete()


class ReadLegalContentTestCase(TestCase):
    def setUp(self):
        self.content_dir = settings.ASSETS_ROOT / 'legal' / 'tos' / 'v2.0'
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil

        cleanup_dir = settings.ASSETS_ROOT / 'legal' / 'tos' / 'v2.0'
        if cleanup_dir.exists():
            shutil.rmtree(cleanup_dir)

    @override_settings(SUPPORTED_LEGAL_LANGUAGES=['en', 'de'])
    def test_returns_localized_content_when_available(self):
        (self.content_dir / 'de.html').write_text('<h1>AGB</h1>', encoding='utf-8')
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content('tos/v2.0', 'de')
        self.assertEqual(result, '<h1>AGB</h1>')

    def test_falls_back_to_default_for_unsupported_locale(self):
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content('tos/v2.0', 'fr')
        self.assertEqual(result, '<h1>TOS</h1>')

    @override_settings(SUPPORTED_LEGAL_LANGUAGES=['en', 'de'])
    def test_falls_back_to_default_language_when_locale_file_missing(self):
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content('tos/v2.0', 'de')
        self.assertEqual(result, '<h1>TOS</h1>')

    def test_returns_empty_string_when_no_content(self):
        result = _read_legal_content('tos/v99.0', 'en')
        self.assertEqual(result, '')

    def test_rejects_path_traversal_in_locale(self):
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content('tos/v2.0', '../../etc/passwd')
        self.assertEqual(result, '<h1>TOS</h1>')


class GetCurrentLegalDocsTestCase(LegalDocCleanSlateTestCase):
    def setUp(self):
        super().setUp()
        self.client = RequestClient()
        self.user = User.objects.create(username=f'legaltest@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='legal-1')
        self.url = reverse('legal_current')

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    @patch('thunderbird_accounts.legal.views._read_legal_content', return_value='<h1>Mock content</h1>')
    def test_returns_current_docs_with_accepted_status(self, mock_read):
        oidc_force_login(self.client, self.user)

        tos = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )
        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.PRIVACY,
            version='2.0',
            is_current=True,
            content_path='privacy/v2.0',
        )

        LegalDocumentResponse.objects.create(
            user=self.user,
            document=tos,
            action=LegalDocumentResponse.Action.ACCEPTED,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        docs = data['documents']
        self.assertEqual(len(docs), 2)

        tos_doc = next(d for d in docs if d['document_type'] == 'tos')
        privacy_doc = next(d for d in docs if d['document_type'] == 'privacy')

        self.assertTrue(tos_doc['accepted'])
        self.assertFalse(privacy_doc['accepted'])
        self.assertEqual(tos_doc['content'], '<h1>Mock content</h1>')
        self.assertEqual(tos_doc['version'], '2.0')

    @patch('thunderbird_accounts.legal.views._read_legal_content', return_value='')
    def test_returns_empty_list_when_no_current_docs(self, mock_read):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='0.9',
            is_current=False,
            content_path='tos/v0.9',
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['documents'], [])

    @patch('thunderbird_accounts.legal.views._read_legal_content', return_value='<h1>Content</h1>')
    def test_passes_locale_param(self, mock_read):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        self.client.get(self.url + '?locale=de')
        mock_read.assert_called_with('tos/v2.0', 'de')

    @patch('thunderbird_accounts.legal.views._read_legal_content', return_value='<h1>Content</h1>')
    def test_defaults_locale_to_en(self, mock_read):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        self.client.get(self.url)
        mock_read.assert_called_with('tos/v2.0', 'en')

    def test_rejects_non_get_methods(self):
        oidc_force_login(self.client, self.user)
        response = self.client.post(self.url, data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 405)

    @patch('thunderbird_accounts.legal.views._read_legal_content', return_value='<h1>Content</h1>')
    def test_declined_doc_not_counted_as_accepted(self, mock_read):
        oidc_force_login(self.client, self.user)

        tos = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        LegalDocumentResponse.objects.create(
            user=self.user,
            document=tos,
            action=LegalDocumentResponse.Action.DECLINED,
        )

        response = self.client.get(self.url)
        data = json.loads(response.content)
        tos_doc = data['documents'][0]
        self.assertFalse(tos_doc['accepted'])


class AcceptLegalDocsTestCase(LegalDocCleanSlateTestCase):
    def setUp(self):
        super().setUp()
        self.client = RequestClient()
        self.user = User.objects.create(username=f'accepttest@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='accept-1')
        self.url = reverse('legal_accept')

    def test_requires_authentication(self):
        response = self.client.post(self.url, data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 302)

    def test_creates_accepted_responses_for_all_current_docs(self):
        oidc_force_login(self.client, self.user)

        tos = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )
        privacy = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.PRIVACY,
            version='2.0',
            is_current=True,
            content_path='privacy/v2.0',
        )

        payload = json.dumps({'source_context': 'sign-up'})
        response = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data['responses']), 2)

        for resp in data['responses']:
            self.assertEqual(resp['action'], 'accepted')

        self.assertTrue(
            LegalDocumentResponse.objects.filter(
                user=self.user, document=tos, action=LegalDocumentResponse.Action.ACCEPTED, source_context='sign-up'
            ).exists()
        )
        self.assertTrue(
            LegalDocumentResponse.objects.filter(
                user=self.user, document=privacy, action=LegalDocumentResponse.Action.ACCEPTED, source_context='sign-up'
            ).exists()
        )

    def test_returns_empty_responses_when_no_current_docs(self):
        oidc_force_login(self.client, self.user)

        payload = json.dumps({})
        response = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['responses'], [])

    def test_source_context_defaults_to_empty(self):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        payload = json.dumps({})
        self.client.post(self.url, data=payload, content_type='application/json')

        resp = LegalDocumentResponse.objects.get(user=self.user)
        self.assertEqual(resp.source_context, '')

    def test_rejects_non_post_methods(self):
        oidc_force_login(self.client, self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class DeclineLegalDocsTestCase(LegalDocCleanSlateTestCase):
    def setUp(self):
        super().setUp()
        self.client = RequestClient()
        self.user = User.objects.create(username=f'declinetest@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='decline-1')
        self.url = reverse('legal_decline')

    def test_requires_authentication(self):
        response = self.client.post(self.url, data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 302)

    def test_creates_declined_responses_and_logs_out(self):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        payload = json.dumps({'source_context': 'dashboard'})
        response = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['redirect_url'], '/')

        self.assertTrue(
            LegalDocumentResponse.objects.filter(
                user=self.user,
                action=LegalDocumentResponse.Action.DECLINED,
                source_context='dashboard',
            ).exists()
        )

    @override_settings(AUTH_SCHEME='oidc')
    @patch('thunderbird_accounts.legal.views.sentry_sdk')
    def test_decline_calls_keycloak_logout_for_oidc_user(self, mock_sentry):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        with patch('thunderbird_accounts.authentication.clients.KeycloakClient') as mock_kc_cls:
            mock_kc = Mock()
            mock_kc_cls.return_value = mock_kc

            payload = json.dumps({})
            self.client.post(self.url, data=payload, content_type='application/json')

            mock_kc.request.assert_called_once()
            call_args = mock_kc.request.call_args[0]
            self.assertEqual(call_args[0], f'users/{self.user.oidc_id}/logout')

    @override_settings(AUTH_SCHEME='oidc')
    @patch('thunderbird_accounts.legal.views.sentry_sdk')
    def test_decline_handles_keycloak_logout_failure(self, mock_sentry):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        with patch('thunderbird_accounts.authentication.clients.KeycloakClient') as mock_kc_cls:
            mock_kc = Mock()
            mock_kc_cls.return_value = mock_kc
            mock_kc.request.side_effect = Exception('Keycloak unavailable')

            payload = json.dumps({})
            response = self.client.post(self.url, data=payload, content_type='application/json')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data['redirect_url'], '/')
            mock_sentry.capture_exception.assert_called_once()

    @override_settings(AUTH_SCHEME='password')
    def test_decline_skips_keycloak_for_password_auth(self):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        with patch('thunderbird_accounts.authentication.clients.KeycloakClient') as mock_kc_cls:
            payload = json.dumps({})
            response = self.client.post(self.url, data=payload, content_type='application/json')

            self.assertEqual(response.status_code, 200)
            mock_kc_cls.assert_not_called()

    def test_rejects_non_post_methods(self):
        oidc_force_login(self.client, self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
