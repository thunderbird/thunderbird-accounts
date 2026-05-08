import json
import time
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from requests import Response as RequestsResponse
from requests.exceptions import RequestException
from rest_framework.test import APIClient

from thunderbird_accounts.authentication.clients import KeycloakClient, RequestMethods
from thunderbird_accounts.authentication.exceptions import MfaCredentialError
from thunderbird_accounts.authentication.mfa import (
    make_pending_totp_cache_key,
    MFA_MANAGEMENT_AUTH_SESSION_KEY,
)
from thunderbird_accounts.authentication.models import User


def _provider_setup_response() -> dict:
    """A representative keycloak-mfa-rest `totp/{id}/setup` payload."""
    return {
        'secret': 'rawsecretvalue123456',
        'encodedSecret': 'MFRG GZDF MZTW Q2LK',
        'otpAuthUri': 'otpauth://totp/Thunderbird%20Accounts%3Atest@example.com?secret=MFRGGZDF',
        'qrCode': 'base64png',
        'digits': 6,
        'period': 30,
        'algorithm': 'SHA1',
    }


class MfaApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            oidc_id='keycloak-user-id',
        )
        self.client.force_authenticate(self.user)
        session = self.client.session
        session[MFA_MANAGEMENT_AUTH_SESSION_KEY] = int(time.time())
        # The provider is self-service: the view forwards the user's stored OIDC access token.
        session['oidc_access_token'] = 'test-user-access-token'
        session.save()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_get_mfa_methods_returns_keycloak_totp_credentials(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [
            {
                'id': 'credential-id',
                'type': 'otp',
                'userLabel': 'Phone',
                'createdDate': 1715000000000,
            }
        ]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(reverse('api_get_mfa_methods'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['methods']['authenticatorApp'],
            {
                'set': True,
                'credentials': [
                    {
                        'id': 'credential-id',
                        'label': 'Phone',
                        'createdDate': 1715000000000,
                        'lastUsedDate': None,
                    }
                ],
            },
        )
        self.assertEqual(response.json()['methods']['recoveryCodes']['set'], False)

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_get_mfa_methods_returns_recovery_codes_credentials(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {
                'id': 'recovery-cred-id',
                'type': 'recovery-authn-codes',
                'userLabel': 'Recovery codes',
                'createdDate': 1715000000000,
                'credentialData': json.dumps({'algorithm': 'SHA-512', 'remaining': 11, 'total': 12}),
            }
        ]

        response = self.client.get(reverse('api_get_mfa_methods'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['methods']['recoveryCodes'],
            {
                'set': True,
                'credentials': [
                    {
                        'id': 'recovery-cred-id',
                        'label': 'Recovery codes',
                        'createdDate': 1715000000000,
                        'lastUsedDate': None,
                        'totalCodes': 12,
                        'remainingCodes': 11,
                    }
                ],
            },
        )

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_get_mfa_methods_requires_keycloak_reauth_when_totp_is_configured(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(reverse('api_get_mfa_methods'))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_get_mfa_methods_reauth_url_uses_same_origin_referer(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(
            reverse('api_get_mfa_methods'),
            HTTP_REFERER='http://testserver/account/security?tab=mfa',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['reauthUrl'],
            '/oidc/mfa-reauth/?next=%2Faccount%2Fsecurity%3Ftab%3Dmfa',
        )

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_get_mfa_methods_reauth_url_ignores_cross_origin_referer(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(
            reverse('api_get_mfa_methods'),
            HTTP_REFERER='http://evil.example.com/manage-mfa',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_get_mfa_methods_allows_unconfigured_totp_without_keycloak_reauth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(reverse('api_get_mfa_methods'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['methods']['authenticatorApp']['set'])

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_totp_setup_caches_provider_secret_and_returns_otpauth_uri(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.start_totp_setup.return_value = _provider_setup_response()

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        # The provider issues the otpauth URI and the display secret; accounts just relays them.
        self.assertEqual(response_data['otpAuthUri'], _provider_setup_response()['otpAuthUri'])
        self.assertEqual(response_data['secret'], _provider_setup_response()['encodedSecret'])
        # The raw secret is cached transiently for the confirm step.
        self.assertEqual(
            cache.get(make_pending_totp_cache_key(self.user.pk)),
            {'secret': _provider_setup_response()['secret']},
        )

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_totp_setup_registers_credential_via_provider(self, mock_keycloak_client: Mock):
        pending_secret = 'rawsecretvalue123456'
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': pending_secret})
        mock_keycloak_client.return_value.register_totp_credential.return_value = {'success': True}
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [
            {'id': 'new-credential-id', 'userLabel': 'Authenticator app'}
        ]

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '123456'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.register_totp_credential.assert_called_once_with(
            user_access_token='test-user-access-token',
            secret=pending_secret,
            code='123456',
            user_label='Authenticator app',
        )
        self.assertIsNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_totp_setup_requires_user_access_token(self, mock_keycloak_client: Mock):
        # No TOTP configured (no step-up), but the user's OIDC access token is missing.
        session = self.client.session
        session.pop('oidc_access_token')
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 401)
        mock_keycloak_client.return_value.start_totp_setup.assert_not_called()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_totp_setup_rejects_invalid_code(self, mock_keycloak_client: Mock):
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': 'rawsecretvalue123456'})
        mock_keycloak_client.return_value.register_totp_credential.side_effect = MfaCredentialError('invalid_code')

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '000000'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        # Pending secret is preserved so the user can retry with a fresh code.
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_totp_setup_rejects_when_setup_expired(self, mock_keycloak_client: Mock):
        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '123456'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        mock_keycloak_client.return_value.register_totp_credential.assert_not_called()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_remove_totp_credential_checks_credential_belongs_to_user(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]

        response = self.client.delete(reverse('api_remove_totp_credential', args=['credential-id']))

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.delete_credential.assert_called_once_with('keycloak-user-id', 'credential-id')

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_remove_totp_credential_requires_recent_keycloak_auth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()

        response = self.client.delete(reverse('api_remove_totp_credential', args=['credential-id']))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')
        mock_keycloak_client.return_value.delete_credential.assert_not_called()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_totp_setup_requires_keycloak_reauth_when_totp_is_configured(self, mock_keycloak_client: Mock):
        session = self.client.session
        session[MFA_MANAGEMENT_AUTH_SESSION_KEY] = int(time.time()) - (settings.MFA_RECENT_AUTH_SECONDS + 1)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')
        self.assertIsNone(cache.get(make_pending_totp_cache_key(self.user.pk)))
        mock_keycloak_client.return_value.start_totp_setup.assert_not_called()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_totp_setup_allows_first_setup_without_keycloak_reauth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []
        mock_keycloak_client.return_value.start_totp_setup.return_value = _provider_setup_response()

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_regenerate_recovery_codes_returns_provider_codes(self, mock_keycloak_client: Mock):
        codes = [f'CODE{index:08d}' for index in range(12)]
        mock_keycloak_client.return_value.regenerate_recovery_codes.return_value = {
            'codes': codes,
            'total': 12,
            'remaining': 12,
        }
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {
                'id': 'recovery-cred-id',
                'type': 'recovery-authn-codes',
                'userLabel': 'Recovery codes',
                'credentialData': json.dumps({'algorithm': 'SHA-512', 'remaining': 12, 'total': 12}),
            }
        ]

        response = self.client.post(reverse('api_regenerate_recovery_codes'))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['codes'], codes)
        self.assertTrue(body['credentials'][0]['totalCodes'] == 12)
        mock_keycloak_client.return_value.regenerate_recovery_codes.assert_called_once_with(
            'test-user-access-token', user_label='Recovery codes'
        )

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_regenerate_recovery_codes_requires_recent_keycloak_auth_when_totp_set(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'cred', 'type': 'otp'}]

        response = self.client.post(reverse('api_regenerate_recovery_codes'))

        self.assertEqual(response.status_code, 403)
        mock_keycloak_client.return_value.regenerate_recovery_codes.assert_not_called()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_remove_recovery_codes_credential_checks_credential_belongs_to_user(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {'id': 'recovery-cred-id', 'type': 'recovery-authn-codes'}
        ]

        response = self.client.delete(reverse('api_remove_recovery_codes_credential', args=['recovery-cred-id']))

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.delete_credential.assert_called_once_with(
            'keycloak-user-id', 'recovery-cred-id'
        )

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_remove_recovery_codes_credential_rejects_unknown_credential(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {'id': 'recovery-cred-id', 'type': 'recovery-authn-codes'}
        ]

        response = self.client.delete(reverse('api_remove_recovery_codes_credential', args=['some-other-id']))

        self.assertEqual(response.status_code, 404)
        mock_keycloak_client.return_value.delete_credential.assert_not_called()


class KeycloakClientMfaTestCase(TestCase):
    """The MFA client methods are thin wrappers over the keycloak-mfa-rest provider,
    reached on the realm path (KEYCLOAK_MFA_API_ENDPOINT) rather than the admin API."""

    USER_TOKEN = 'user-access-token'

    def test_start_totp_setup_calls_provider_setup_endpoint(self):
        client = KeycloakClient()

        with patch.object(client, 'request') as mock_request:
            mock_request.return_value.json.return_value = _provider_setup_response()
            result = client.start_totp_setup(self.USER_TOKEN)

        endpoint, method = mock_request.call_args.args[:2]
        self.assertEqual(endpoint, 'totp/setup')
        self.assertEqual(method, RequestMethods.GET)
        self.assertEqual(mock_request.call_args.kwargs['base_url'], settings.KEYCLOAK_MFA_API_ENDPOINT)
        # The user's OIDC token is forwarded so the provider acts on its subject.
        self.assertEqual(mock_request.call_args.kwargs['access_token'], self.USER_TOKEN)
        self.assertEqual(result, _provider_setup_response())

    def test_register_totp_credential_posts_secret_and_code(self):
        client = KeycloakClient()

        with patch.object(client, 'request') as mock_request:
            mock_request.return_value.json.return_value = {'success': True, 'label': 'Authenticator app'}
            client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '123456', 'Authenticator app')

        endpoint, method = mock_request.call_args.args[:2]
        self.assertEqual(endpoint, 'totp/register')
        self.assertEqual(method, RequestMethods.POST)
        self.assertEqual(mock_request.call_args.kwargs['base_url'], settings.KEYCLOAK_MFA_API_ENDPOINT)
        self.assertEqual(mock_request.call_args.kwargs['access_token'], self.USER_TOKEN)
        self.assertEqual(
            mock_request.call_args.kwargs['json_data'],
            {'secret': 'rawsecret', 'code': '123456', 'deviceName': 'Authenticator app', 'overwrite': True},
        )

    def test_register_totp_credential_raises_mfa_error_on_client_error(self):
        client = KeycloakClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 400
        failing_response._content = json.dumps({'error': 'invalid_code'}).encode()

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(MfaCredentialError) as ctx:
                client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '000000', 'Authenticator app')

        self.assertEqual(ctx.exception.error_code, 'invalid_code')

    def test_register_totp_credential_reraises_upstream_errors(self):
        client = KeycloakClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 502

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(RequestException):
                client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '000000', 'Authenticator app')

    def test_regenerate_recovery_codes_posts_to_provider(self):
        client = KeycloakClient()

        with patch.object(client, 'request') as mock_request:
            mock_request.return_value.json.return_value = {'codes': ['AAAA', 'BBBB'], 'total': 2, 'remaining': 2}
            result = client.regenerate_recovery_codes(self.USER_TOKEN, user_label='Recovery codes')

        endpoint, method = mock_request.call_args.args[:2]
        self.assertEqual(endpoint, 'recovery-codes/regenerate')
        self.assertEqual(method, RequestMethods.POST)
        self.assertEqual(mock_request.call_args.kwargs['base_url'], settings.KEYCLOAK_MFA_API_ENDPOINT)
        self.assertEqual(mock_request.call_args.kwargs['access_token'], self.USER_TOKEN)
        self.assertEqual(mock_request.call_args.kwargs['json_data'], {'deviceName': 'Recovery codes'})
        self.assertEqual(result['codes'], ['AAAA', 'BBBB'])
