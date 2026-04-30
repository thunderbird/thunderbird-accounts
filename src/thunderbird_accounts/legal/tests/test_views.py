from django.apps import apps
from pathlib import Path
import json
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.core.tests.utils import oidc_force_login
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.legal.views import _read_legal_content
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.subscription.models import Subscription


class LegalDocCleanSlateTestCase(TestCase):
    """Clears seeded LegalDocument rows so each test starts with a known-empty table."""

    def setUp(self):
        super().setUp()
        LegalDocument.objects.all().delete()


class ReadLegalContentTestCase(TestCase):
    def setUp(self):
        self.legal_app_path = apps.get_app_config("legal").path
        self.version = 'v999.0'

        self.content_dir = Path(self.legal_app_path, 'templates', 'tos', self.version).resolve()
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        if self.content_dir.exists():
            shutil.rmtree(self.content_dir)

    @override_settings(SUPPORTED_LEGAL_LANGUAGES=['en', 'de'])
    def test_returns_localized_content_when_available(self):
        (self.content_dir / 'de.html').write_text('<h1>AGB</h1>', encoding='utf-8')
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content(f'tos/{self.version}', 'de')
        self.assertEqual(result, '<h1>AGB</h1>')

    def test_falls_back_to_default_for_unsupported_locale(self):
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content(f'tos/{self.version}', 'not-a-language')
        self.assertEqual(result, '<h1>TOS</h1>')

    @override_settings(SUPPORTED_LEGAL_LANGUAGES=['en', 'de'])
    def test_falls_back_to_default_language_when_locale_file_missing(self):
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content(f'tos/{self.version}', 'de')
        self.assertEqual(result, '<h1>TOS</h1>')

    def test_rejects_path_traversal_in_locale(self):
        (self.content_dir / 'en.html').write_text('<h1>TOS</h1>', encoding='utf-8')
        result = _read_legal_content(f'tos/{self.version}', '../../etc/passwd')
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

    def test_duplicate_accept_does_not_create_new_responses(self):
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
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

        payload = json.dumps({'source_context': 'sign-up'})

        response1 = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)
        self.assertEqual(len(data1['responses']), 2)

        response2 = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)
        self.assertEqual(len(data2['responses']), 0)

        self.assertEqual(
            LegalDocumentResponse.objects.filter(
                user=self.user, action=LegalDocumentResponse.Action.ACCEPTED
            ).count(),
            2,
        )

    def test_duplicate_decline_does_not_create_new_responses(self):
        oidc_force_login(self.client, self.user)

        # Give user an active subscription so decline doesn't delete user
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        payload = json.dumps({'source_context': 'dashboard'})
        decline_url = self.url.replace('accept', 'decline')

        response1 = self.client.post(decline_url, data=payload, content_type='application/json')
        self.assertEqual(response1.status_code, 200)

        response2 = self.client.post(decline_url, data=payload, content_type='application/json')
        self.assertEqual(response2.status_code, 200)

        self.assertEqual(
            LegalDocumentResponse.objects.filter(
                user=self.user, action=LegalDocumentResponse.Action.DECLINED
            ).count(),
            1,
        )

    def test_rejects_non_post_methods(self):
        oidc_force_login(self.client, self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class DeclineLegalDocsTestCase(LegalDocCleanSlateTestCase):
    """Tests the decline flow for users WITH an active subscription (redirect to contact, no deletion)."""

    def setUp(self):
        super().setUp()
        self.client = RequestClient()
        self.user = User.objects.create(username=f'declinetest@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='decline-1')
        self.url = reverse('legal_decline')

    def _give_active_subscription(self):
        Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)

    def test_requires_authentication(self):
        response = self.client.post(self.url, data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 302)

    def test_creates_declined_responses_and_redirects_to_contact(self):
        self._give_active_subscription()
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
        self.assertEqual(data['redirect_url'], '/contact')

        self.assertTrue(
            LegalDocumentResponse.objects.filter(
                user=self.user,
                action=LegalDocumentResponse.Action.DECLINED,
                source_context='dashboard',
            ).exists()
        )

    def test_decline_with_subscription_sets_warning_message(self):
        self._give_active_subscription()
        oidc_force_login(self.client, self.user)

        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        payload = json.dumps({})
        response = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        from django.contrib.messages import get_messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('contact support', str(messages[0]).lower())

    def test_rejects_non_post_methods(self):
        oidc_force_login(self.client, self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


@patch('thunderbird_accounts.mail.clients.MailClient._delete_principal')
@patch('thunderbird_accounts.authentication.clients.KeycloakClient.request')
class DeclineLegalDocsDeleteUserTestCase(LegalDocCleanSlateTestCase):
    """Tests that declining TOS without an active subscription deletes all user data."""

    def setUp(self):
        super().setUp()
        self.client = RequestClient()
        self.subdomain = settings.PRIMARY_EMAIL_DOMAIN
        self.user = User.objects.create(
            username=f'deletetest@{self.subdomain}',
            email='deletetest@example.com',
            oidc_id='delete-oidc-1',
        )
        self.url = reverse('legal_decline')
        self.tos = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

    def test_deletes_user_from_keycloak_and_db(self, mock_kc_request, mock_delete_principal):
        oidc_force_login(self.client, self.user)
        payload = json.dumps({'source_context': 'dashboard'})
        response = self.client.post(self.url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['redirect_url'], '/')

        mock_kc_request.assert_called_once()
        endpoint, method = mock_kc_request.call_args[0]
        self.assertEqual(endpoint, f'users/{self.user.oidc_id}')

        with self.assertRaises(User.DoesNotExist):
            self.user.refresh_from_db()

    def test_deletes_stalwart_account_when_present(self, mock_kc_request, mock_delete_principal):
        account = Account.objects.create(name='deletetest', user=self.user)
        Email.objects.create(
            address=self.user.username,
            type=Email.EmailType.PRIMARY,
            account=account,
        )

        oidc_force_login(self.client, self.user)
        payload = json.dumps({})
        self.client.post(self.url, data=payload, content_type='application/json')

        mock_kc_request.assert_called_once()
        mock_delete_principal.assert_called_once()

        with self.assertRaises(User.DoesNotExist):
            self.user.refresh_from_db()
        with self.assertRaises(Account.DoesNotExist):
            account.refresh_from_db()

    def test_skips_stalwart_when_no_email(self, mock_kc_request, mock_delete_principal):
        oidc_force_login(self.client, self.user)
        payload = json.dumps({})
        self.client.post(self.url, data=payload, content_type='application/json')

        mock_kc_request.assert_called_once()
        mock_delete_principal.assert_not_called()

        with self.assertRaises(User.DoesNotExist):
            self.user.refresh_from_db()

    def test_decline_response_is_cascade_deleted_with_user(self, mock_kc_request, mock_delete_principal):
        oidc_force_login(self.client, self.user)
        payload = json.dumps({'source_context': 'dashboard'})
        self.client.post(self.url, data=payload, content_type='application/json')

        with self.assertRaises(User.DoesNotExist):
            self.user.refresh_from_db()

        self.assertFalse(
            LegalDocumentResponse.objects.filter(user_id=self.user.pk).exists()
        )

    @patch('thunderbird_accounts.authentication.utils.sentry_sdk')
    def test_still_deletes_db_user_on_keycloak_failure(self, mock_sentry, mock_kc_request, mock_delete_principal):
        from thunderbird_accounts.authentication.exceptions import DeleteUserError

        mock_kc_request.side_effect = DeleteUserError(error='Connection refused', oidc_id=self.user.oidc_id)

        oidc_force_login(self.client, self.user)
        payload = json.dumps({})
        response = self.client.post(self.url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        mock_sentry.capture_exception.assert_called_once()

        with self.assertRaises(User.DoesNotExist):
            self.user.refresh_from_db()
