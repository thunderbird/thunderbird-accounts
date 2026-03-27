import json
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Domain, Email


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

    def test_already_used_alias(self):
        """Ensure that creating an email alias that is already in-use will error out."""
        email_alias_url = reverse('add_email_alias')

        Email(address=f'admin@{settings.PRIMARY_EMAIL_DOMAIN}').save()

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
