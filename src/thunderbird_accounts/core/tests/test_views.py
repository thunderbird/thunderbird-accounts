from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase, Client as RequestClient
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.models import Account


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

    def test_unauthenticated_user_can_access_privacy_page(self):
        """Test that unauthenticated users can access the /privacy public route."""
        response = self.client.get('/privacy')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_unauthenticated_user_can_access_terms_page(self):
        """Test that unauthenticated users can access the /terms public route."""
        response = self.client.get('/terms')
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

    def test_needs_tos_acceptance_false_when_no_current_docs(self):
        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['needs_tos_acceptance'])

    def test_needs_tos_acceptance_true_when_docs_not_accepted(self):
        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['needs_tos_acceptance'])

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
        self.assertFalse(response.context['needs_tos_acceptance'])

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
        self.assertTrue(response.context['needs_tos_acceptance'])

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
        self.assertTrue(response.context['needs_tos_acceptance'])

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
        self.assertFalse(response.context['needs_tos_acceptance'])

    def test_needs_tos_acceptance_ignores_non_current_docs(self):
        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='0.9',
            is_current=False,
            content_path='tos/v0.9',
        )

        response = self._login_and_get_home()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['needs_tos_acceptance'])
