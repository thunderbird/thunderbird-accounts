import json
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase, Client as RequestClient
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
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
        self.assertTemplateUsed(response, 'mail/index.html')

    def test_unauthenticated_user_can_access_terms_page(self):
        """Test that unauthenticated users can access the /terms public route."""
        response = self.client.get('/terms')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mail/index.html')

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
            self.assertTemplateUsed(response, 'mail/index.html')

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
                    self.assertTemplateUsed(response, 'mail/index.html')


class AddEmailAliasTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
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


class ZendeskContactFieldsTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    def test_contact_fields_success_filters_and_transforms(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.get_ticket_fields.return_value = {
            'success': True,
            'data': {
                'ticket_form': {'id': 123, 'name': 'Support'},
                'ticket_fields': [
                    {
                        'id': 1,
                        'title': 'Subject',
                        'description': 'Subject field',
                        'required': True,
                        'type': 'subject',
                        'active': True,
                        'visible_in_portal': True,
                        'editable_in_portal': True,
                    },
                    {
                        'id': 2,
                        'title': 'Category',
                        'description': 'Choose a category',
                        'required': False,
                        'type': 'tagger',
                        'active': True,
                        'visible_in_portal': True,
                        'editable_in_portal': True,
                        'custom_field_options': [
                            {'id': 21, 'name': 'General', 'value': 'general', 'extra': 'ignored'},
                            {'id': 22, 'name': 'Billing', 'value': 'billing'},
                        ],
                    },
                    {
                        # Should be filtered out (not editable in portal)
                        'id': 3,
                        'title': 'Internal',
                        'description': 'Internal only',
                        'required': False,
                        'type': 'text',
                        'active': True,
                        'visible_in_portal': True,
                        'editable_in_portal': False,
                    },
                ],
            },
        }

        url = reverse('contact_fields')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())

        self.assertTrue(payload['success'])
        self.assertEqual(payload['ticket_form'], {'id': 123})
        self.assertIn('ticket_fields', payload)

        # Only two fields should pass the filter
        fields = payload['ticket_fields']
        self.assertEqual(len(fields), 2)

        # Field 1 minimal keys + values
        f1 = next(f for f in fields if f['id'] == 1)
        self.assertEqual(
            {k: f1[k] for k in ['id', 'title', 'description', 'required', 'type']},
            {'id': 1, 'title': 'Subject', 'description': 'Subject field', 'required': True, 'type': 'subject'},
        )
        self.assertNotIn('custom_field_options', f1)

        # Field 2 options trimmed to id/name/value
        f2 = next(f for f in fields if f['id'] == 2)
        self.assertEqual(f2['title'], 'Category')
        self.assertIn('custom_field_options', f2)
        self.assertEqual(
            f2['custom_field_options'],
            [
                {'id': 21, 'name': 'General', 'value': 'general'},
                {'id': 22, 'name': 'Billing', 'value': 'billing'},
            ],
        )

        # Ensure client was called once
        instance.get_ticket_fields.assert_called_once()

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    def test_contact_fields_error_from_backend(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.get_ticket_fields.return_value = {'success': False, 'error': 'Boom'}

        url = reverse('contact_fields')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload, {'success': False, 'error': 'Boom'})

    def test_contact_fields_method_not_allowed(self):
        url = reverse('contact_fields')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 405)
