from typing import Optional
from unittest.mock import patch

import freezegun
from django.conf import settings
from django.contrib.admin import AdminSite
from django.http import HttpRequest
from django.test import TestCase, Client as RequestClient
from django.urls import reverse
from requests import Response

from thunderbird_accounts.authentication.admin import CustomUserAdmin
from thunderbird_accounts.authentication.admin.forms import CustomNewUserForm
from thunderbird_accounts.authentication.clients import RequestMethods
from thunderbird_accounts.authentication.exceptions import InvalidDomainError
from thunderbird_accounts.authentication.middleware import AccountsOIDCBackend
from thunderbird_accounts.authentication.models import User

FAKE_OIDC_UUID = '39a7b5e8-7a64-45e3-acf1-ca7d314bfcec'
MOCKED_RESPONSE_HEADER = 'X-Mocked-Response'


def mock_keycloak_client_request(_self,
                                 endpoint: str,
                                 method: RequestMethods = RequestMethods.GET,
                                 json_data: Optional[dict] = None,
                                 data: Optional[dict | list | str] = None,
                                 params: Optional[dict] = None):
    fake_uuid = FAKE_OIDC_UUID
    fake_url = 'http://example.org/admin/realms/tbpro'

    fake_response = Response()
    fake_response.status_code = 200
    fake_response.headers.update({
        'MOCKED_RESPONSE_HEADER': 'True',
    })

    # If we need to override specific endpoints, here's where to do it!
    if endpoint == 'users':
        fake_response.status_code = 201
        fake_response.headers.update({
            'Location': f'{fake_url}/users/{fake_uuid}'
        })

    return fake_response


@patch('thunderbird_accounts.authentication.clients.KeycloakClient.request', mock_keycloak_client_request)
class AdminCreateUserTestCase(TestCase):
    def setUp(self):
        self.subdomain = settings.ALLOWED_EMAIL_DOMAINS[0] if len(settings.ALLOWED_EMAIL_DOMAINS) > 0 else 'example.org'
        self.default_form_data = dict({k.name: None for k in User()._meta.fields})

    def _build_form(self, form_data):
        user_admin = CustomUserAdmin(User, AdminSite())
        fake_request = HttpRequest()
        return user_admin.get_form(fake_request)(form_data)

    def test_failed_username_validation(self):
        # Bad username
        form_data = {
            'username': f'frog',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        with self.assertRaises(ValueError):
            form.save(True)

    def test_failed_email_validation(self):
        settings.ALLOWED_EMAIL_DOMAINS = ['example.org']

        # Bad email domain
        form_data = {
            'username': 'frog@example.com',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        with self.assertRaises(InvalidDomainError):
            form.save(True)

        # No email
        form_data = {
            'username': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('email', form.errors)

    def test_failed_timezone_validation(self):
        # Bad username
        form_data = {
            'username': f'frog',
            'email': 'frog@example.com',
            'timezone': 'America/Victoria',
        }

        form = self._build_form(form_data)

        self.assertTrue(len(form.errors) > 0)
        self.assertIn('timezone', form.errors)

    def test_successful_minimum(self):
        form_data = {
            'username': f'frog@{self.subdomain}',
            'email': 'frog@example.com',
            'timezone': 'America/Toronto',
        }

        form = self._build_form(form_data)

        user = form.save(True)
        # We should have a user, they should have a pk (saved to db), and our fake oidc id
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.oidc_id, FAKE_OIDC_UUID)


class AccountsOIDCBackendTestCase(TestCase):
    def setUp(self):
        self.claim_oidc_id = 'abc123'
        self.claim_email = 'user@example.org'
        with freezegun.freeze_time('Apr 4th, 2000'):
            self.user = User.objects.create(
                oidc_id=self.claim_oidc_id, username='test@example.org', email=self.claim_email
            )
            self.user.save()
            self.user.refresh_from_db()
        self.backend = AccountsOIDCBackend()

    def test_filter_users_by_claims_no_fallback(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = False

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})
        assert len(query) == 1

        query = self.backend.filter_users_by_claims(
            {'sub': f'{self.claim_oidc_id}_not_the_actual_id_anymore', 'email': self.claim_email}
        )
        assert len(query) == 0

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting

    def test_filter_users_by_claims_with_fallback(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = True

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})
        assert len(query) == 1

        query = self.backend.filter_users_by_claims(
            {'sub': f'{self.claim_oidc_id}_not_the_actual_id_anymore', 'email': self.claim_email}
        )
        assert len(query) == 1

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting

    def test_filter_users_by_claims_with_fallback_with_duplicates(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = True

        # Ensure the user doesn't have an oidc id
        self.user.oidc_id = None
        self.user.save()

        user_duplicates = [
            User.objects.create(oidc_id=None, email=self.claim_email, username='test'),
            User.objects.create(oidc_id=None, email=self.claim_email, username='test2'),
            User.objects.create(oidc_id=None, email=self.claim_email, username='test3'),
        ]

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})

        assert len(query) == 1
        self.assertEqual(self.user.pk, query[0].pk)
        self.assertEqual(self.claim_email, query[0].email)

        # Ensure the older models were deleted
        for user in user_duplicates:
            with self.assertRaises(User.DoesNotExist):
                user.refresh_from_db()

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting


class LoginRequiredTestCase(TestCase):
    # (URL reverse key, expected response status code),
    login_required_keys = [
        ('self_serve_home', 302),  # This one is a redirect
        ('self_serve_account_info', 302),
        ('self_serve_app_password', 302),
        ('self_serve_connection_info', 302),
        ('self_serve_subscription', 302),
        ('self_serve_subscription_success', 302),
    ]

    def test_logged_out(self):
        client = RequestClient()
        login_url = reverse(settings.LOGIN_URL)

        for key, _ in self.login_required_keys:
            url = reverse(key)
            self.assertTrue(url)

            response = client.get(url, follow=False)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(login_url))

    def test_logged_in(self):
        client = RequestClient()
        user = User.objects.get_or_create(username='test', oidc_id='1234')[0]
        client.force_login(user)

        for key, status in self.login_required_keys:
            url = reverse(key)
            self.assertTrue(url)

            response = client.get(url, follow=False)
            self.assertEqual(response.status_code, status)
            self.assertTrue(response.request['PATH_INFO'].startswith(url))
