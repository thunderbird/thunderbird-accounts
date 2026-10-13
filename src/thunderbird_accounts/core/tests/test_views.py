import json
import re
from django.utils.html import strip_tags
from unittest.mock import patch, Mock

from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import SimpleTestCase, TestCase, Client as RequestClient, RequestFactory
from django.urls import reverse
from pathlib import Path

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.core.tests.utils import build_stalwart_account
from thunderbird_accounts.core.views import PUBLIC_VUE_ROUTES, home
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.subscription.models import Subscription


class PublicVueRouteSyncTestCase(SimpleTestCase):
    """Test that public routes stay in sync between Vue and Django"""

    def test_django_public_vue_routes_match_vue_router_public_routes(self):
        vue_public_routes = self._extract_vue_public_routes()

        self.assertSetEqual(vue_public_routes, PUBLIC_VUE_ROUTES)

    def _extract_vue_public_routes(self):
        router_path = Path(settings.BASE_DIR) / 'assets' / 'app' / 'vue' / 'router.ts'
        router_source = router_path.read_text()
        route_matches = list(re.finditer(r"^\s+path:\s*'([^']+)'", router_source, re.MULTILINE))
        public_routes = set()

        for index, route_match in enumerate(route_matches):
            route_end = route_matches[index + 1].start() if index + 1 < len(route_matches) else len(router_source)
            route_definition = router_source[route_match.start() : route_end]
            if not re.search(r'isPublic:\s*true\b', route_definition):
                continue

            path = route_match.group(1)
            if self._is_concrete_vue_path(path):
                public_routes.add(path)

        return public_routes

    @staticmethod
    def _is_concrete_vue_path(path):
        return path.startswith('/') and ':' not in path and '*' not in path and path != '/'


class HomeViewRedirectTestCase(TestCase):
    """Test redirect behavior for authenticated and unauthenticated users."""

    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        self.account = Account.objects.create(name=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)

    def test_unauthenticated_user_redirected_to_login_for_home(self):
        """Test that unauthenticated users are redirected to login when accessing home."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))

    def test_unauthenticated_user_redirected_to_login_for_non_public_routes(self):
        """Test that unauthenticated users are redirected to login for non-public routes."""
        non_public_paths = ['/dashboard', '/mail', '/some-other-path']
        for path in non_public_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse('login'))

    def test_unauthenticated_user_can_access_public_vue_routes(self):
        """Test that unauthenticated users can access public Vue routes."""
        for path in PUBLIC_VUE_ROUTES:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'index.html')

    def test_authenticated_user_can_access_home(self):
        """Test that authenticated users can access home without redirect."""
        self.client.force_login(self.user)

        # Mock OIDC session data to prevent SessionRefresh middleware from redirecting
        session = self.client.session
        session['oidc_id_token_expiration'] = 9999999999  # Far future timestamp
        session.save()

        with patch('thunderbird_accounts.mail.views.MailClient') as mock_mail_client:
            mock_instance = Mock()
            mock_instance.get_account.return_value = {
                'description': 'Test User',
                'secrets': [],
                'emails': [f'test@{settings.PRIMARY_EMAIL_DOMAIN}'],
            }
            mock_mail_client.return_value = mock_instance

            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'index.html')

    def test_authenticated_user_can_access_any_path(self):
        """Test that authenticated users can access any path without redirect."""
        self.client.force_login(self.user)

        # Mock OIDC session data to prevent SessionRefresh middleware from redirecting
        session = self.client.session
        session['oidc_id_token_expiration'] = 9999999999  # Far future timestamp
        session.save()

        paths = ['/dashboard', '/mail', '/privacy', '/terms']

        for path in paths:
            with self.subTest(path=path):
                with patch('thunderbird_accounts.mail.views.MailClient') as mock_mail_client:
                    mock_instance = Mock()
                    mock_instance.get_account.return_value = {
                        'description': 'Test User',
                        'secrets': [],
                        'emails': [f'test@{settings.PRIMARY_EMAIL_DOMAIN}'],
                    }
                    mock_mail_client.return_value = mock_instance

                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, 'index.html')


class HomeViewTypedAccountTestCase(TestCase):
    @patch('thunderbird_accounts.core.views.MailClient')
    def test_typed_account_preserves_mail_page_data(self, mock_mail_client_cls):
        user = User.objects.create(username=f'typed@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='typed-home')
        Account.objects.create(name=user.username, user=user)
        Subscription.objects.create(user=user, status=Subscription.StatusValues.ACTIVE)
        mock_mail_client_cls.return_value.get_account.return_value = build_stalwart_account(
            email_address=user.username,
            aliases={
                '0': {
                    'enabled': True,
                    'name': 'typed',
                    'domainId': 'alias-domain-id',
                    'fullAddress': 'typed@example.com',
                }
            },
            credentials={
                'desktop-password': {
                    '@type': 'AppPassword',
                    'description': 'Desktop',
                    'secret': '********',
                    'permissions': {'@type': 'Inherit'},
                    'allowedIps': {},
                },
                'appointment-password': {
                    '@type': 'AppPassword',
                    'description': f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}{user.username}',
                    'secret': '********',
                    'permissions': {'@type': 'Inherit'},
                    'allowedIps': {},
                },
            },
        )
        request = RequestFactory().get('/')
        request.user = user
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)

        response = home(request)

        page_data = json.loads(strip_tags(response.context_data['page_load_data_script']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page_data['userDisplayName'], None)
        self.assertEqual(page_data['emailAddresses'], [user.username, 'typed@example.com'])
        self.assertEqual(page_data['appPasswords'], ['Desktop'])


class HomeViewNeedsTosAcceptanceTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'tostest@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='tos-1')
        self.account = Account.objects.create(name=f'tostest@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)

        # Delete all existing legal documents so that we can test the absence of documents as well
        LegalDocument.objects.all().delete()

    def _login_and_get_home(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['oidc_id_token_expiration'] = 9999999999
        session.save()

        with patch('thunderbird_accounts.mail.views.MailClient') as mock_mail_client:
            mock_instance = Mock()
            mock_instance.get_account.return_value = {
                'description': 'Test User',
                'secrets': [],
                'emails': [f'tostest@{settings.PRIMARY_EMAIL_DOMAIN}'],
            }
            mock_mail_client.return_value = mock_instance
            return self.client.get('/')

    def _retrieve_json_blob(self, response) -> dict:
        """We inject a javascript script with a plain json blob.
        So for testing we can just strip the script tags off and load it up."""
        blob = response.context['page_load_data_script']
        blob = strip_tags(blob)
        return json.loads(blob)

    def test_needs_tos_acceptance_false_when_no_current_docs(self):
        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertFalse(blob.get('needsTosAcceptance'))

    def test_needs_tos_acceptance_true_when_docs_not_accepted(self):
        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertTrue(blob.get('needsTosAcceptance'))

    def test_needs_tos_acceptance_false_when_all_docs_accepted(self):
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

        LegalDocumentResponse.objects.create(
            user=self.user,
            document=tos,
            action=LegalDocumentResponse.Action.ACCEPTED,
        )
        LegalDocumentResponse.objects.create(
            user=self.user,
            document=privacy,
            action=LegalDocumentResponse.Action.ACCEPTED,
        )

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertFalse(blob.get('needsTosAcceptance'))

    def test_needs_tos_acceptance_true_when_partially_accepted(self):
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

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertTrue(blob.get('needsTosAcceptance'))

    def test_needs_tos_acceptance_true_when_only_declined(self):
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

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertTrue(blob.get('needsTosAcceptance'))

    def test_needs_tos_acceptance_false_with_duplicate_acceptances(self):
        """Duplicate acceptance responses should not cause the check to fail."""
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

        # Force duplicate responses
        LegalDocumentResponse.objects.create(
            user=self.user,
            document=tos,
            action=LegalDocumentResponse.Action.ACCEPTED,
        )
        LegalDocumentResponse.objects.create(
            user=self.user,
            document=tos,
            action=LegalDocumentResponse.Action.ACCEPTED,
        )
        LegalDocumentResponse.objects.create(
            user=self.user,
            document=privacy,
            action=LegalDocumentResponse.Action.ACCEPTED,
        )

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertFalse(blob.get('needsTosAcceptance'))

    def test_needs_tos_acceptance_ignores_non_current_docs(self):
        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='0.9',
            is_current=False,
            content_path='tos/v0.9',
        )

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        blob = self._retrieve_json_blob(response)
        self.assertFalse(blob.get('needsTosAcceptance'))
