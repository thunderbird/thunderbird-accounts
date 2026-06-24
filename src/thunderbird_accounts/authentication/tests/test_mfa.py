import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from requests import Response as RequestsResponse
from requests.exceptions import RequestException
from rest_framework.test import APIClient

from thunderbird_accounts.authentication.clients import KeycloakMfaClient, RequestMethods
from thunderbird_accounts.authentication.exceptions import (
    MfaCredentialError,
    MfaSessionExpiredError,
    MfaStepUpRequiredError,
)
from thunderbird_accounts.authentication.mfa import (
    make_pending_totp_cache_key,
    MFA_MANAGEMENT_AUTH_SESSION_KEY,
    MFA_REST_ERROR_ALREADY_CONFIGURED,
    MFA_REST_ERROR_STEP_UP_REQUIRED,
    MFA_REST_ERROR_TOTP_NOT_CONFIGURED,
)
from thunderbird_accounts.authentication.mfa_management import get_user_access_token
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.views import MfaReauthenticationRequestView


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
        self.mfa_provider_patcher = patch('thunderbird_accounts.authentication.mfa_management.KeycloakMfaClient')
        self.mock_mfa_client = self.mfa_provider_patcher.start()
        self.addCleanup(self.mfa_provider_patcher.stop)

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
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

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
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

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_get_mfa_methods_requires_keycloak_reauth_when_totp_is_configured(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(reverse('api_get_mfa_methods'))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
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

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
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

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_get_mfa_methods_allows_unconfigured_totp_without_keycloak_reauth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.get(reverse('api_get_mfa_methods'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['methods']['authenticatorApp']['set'])

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_start_totp_setup_caches_provider_secret_and_returns_otpauth_uri(self, mock_keycloak_client: Mock):
        self.mock_mfa_client.return_value.start_totp_setup.return_value = _provider_setup_response()

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

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_confirm_totp_setup_registers_credential_via_provider(self, mock_keycloak_client: Mock):
        pending_secret = 'rawsecretvalue123456'
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': pending_secret})
        self.mock_mfa_client.return_value.register_totp_credential.return_value = {'success': True}
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [
            {'id': 'new-credential-id', 'userLabel': 'Authenticator app'}
        ]

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '123456'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.mock_mfa_client.return_value.register_totp_credential.assert_called_once_with(
            user_access_token='test-user-access-token',
            secret=pending_secret,
            code='123456',
            user_label='Authenticator app',
        )
        self.assertIsNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_start_totp_setup_requires_user_access_token(self, mock_keycloak_client: Mock):
        # No TOTP configured (no step-up), but the user's OIDC access token is missing.
        session = self.client.session
        session.pop('oidc_access_token')
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 401)
        self.mock_mfa_client.return_value.start_totp_setup.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_confirm_totp_setup_rejects_invalid_code(self, mock_keycloak_client: Mock):
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': 'rawsecretvalue123456'})
        self.mock_mfa_client.return_value.register_totp_credential.side_effect = MfaCredentialError('invalid_code')

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '000000'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        # Pending secret is preserved so the user can retry with a fresh code.
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_confirm_totp_setup_maps_session_expired_to_relogin(self, mock_keycloak_client: Mock):
        # The forwarded access token can expire while the user lingers on the code step;
        # surface a re-login prompt (401) instead of a generic 502.
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': 'rawsecretvalue123456'})
        self.mock_mfa_client.return_value.register_totp_credential.side_effect = MfaSessionExpiredError()

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '123456'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        # Pending secret is preserved so the user can retry after signing in again.
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_start_totp_setup_maps_session_expired_to_relogin(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []
        self.mock_mfa_client.return_value.start_totp_setup.side_effect = MfaSessionExpiredError()

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_confirm_totp_setup_maps_already_configured_to_conflict(self, mock_keycloak_client: Mock):
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': 'rawsecretvalue123456'})
        self.mock_mfa_client.return_value.register_totp_credential.side_effect = MfaCredentialError(
            MFA_REST_ERROR_ALREADY_CONFIGURED
        )

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '123456'},
            content_type='application/json',
        )

        # Registration is enrollment-only on the provider; the user must remove the
        # existing authenticator first.
        self.assertEqual(response.status_code, 409)
        self.assertIn('already set up', response.json()['error'])

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_confirm_totp_setup_rejects_when_setup_expired(self, mock_keycloak_client: Mock):
        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '123456'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.mock_mfa_client.return_value.register_totp_credential.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_remove_totp_credential_checks_credential_belongs_to_user(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = []

        response = self.client.delete(reverse('api_remove_totp_credential', args=['credential-id']))

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.delete_credential.assert_called_once_with('keycloak-user-id', 'credential-id')

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_remove_last_totp_credential_cascades_recovery_codes(self, mock_keycloak_client: Mock):
        # Recovery codes are a backup for the authenticator: removing the last
        # authenticator must remove them too, or the account is left codes-only and
        # quietly loses MFA entirely once the codes run out.
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {'id': 'recovery-cred-id', 'type': 'recovery-authn-codes'}
        ]

        response = self.client.delete(reverse('api_remove_totp_credential', args=['credential-id']))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['recoveryCodesRemoved'])
        mock_keycloak_client.return_value.delete_credential.assert_any_call('keycloak-user-id', 'credential-id')
        mock_keycloak_client.return_value.delete_credential.assert_any_call('keycloak-user-id', 'recovery-cred-id')

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_remove_totp_credential_keeps_recovery_codes_when_other_authenticators_remain(
        self, mock_keycloak_client: Mock
    ):
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [
            {'id': 'credential-id', 'type': 'otp'},
            {'id': 'other-credential-id', 'type': 'otp'},
        ]

        response = self.client.delete(reverse('api_remove_totp_credential', args=['credential-id']))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['recoveryCodesRemoved'])
        mock_keycloak_client.return_value.delete_credential.assert_called_once_with('keycloak-user-id', 'credential-id')
        mock_keycloak_client.return_value.get_recovery_codes_credentials.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_remove_totp_credential_requires_recent_keycloak_auth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()

        response = self.client.delete(reverse('api_remove_totp_credential', args=['credential-id']))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')
        mock_keycloak_client.return_value.delete_credential.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_start_totp_setup_requires_keycloak_reauth_when_totp_is_configured(self, mock_keycloak_client: Mock):
        session = self.client.session
        session[MFA_MANAGEMENT_AUTH_SESSION_KEY] = int(time.time()) - (settings.MFA_RECENT_AUTH_SECONDS + 1)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'credential-id', 'type': 'otp'}]

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')
        self.assertIsNone(cache.get(make_pending_totp_cache_key(self.user.pk)))
        self.mock_mfa_client.return_value.start_totp_setup.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_start_totp_setup_allows_first_setup_without_keycloak_reauth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []
        self.mock_mfa_client.return_value.start_totp_setup.return_value = _provider_setup_response()

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_regenerate_recovery_codes_returns_provider_codes(self, mock_keycloak_client: Mock):
        codes = [f'CODE{index:08d}' for index in range(12)]
        self.mock_mfa_client.return_value.regenerate_recovery_codes.return_value = {
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
        self.mock_mfa_client.return_value.regenerate_recovery_codes.assert_called_once_with(
            'test-user-access-token', user_label='Recovery codes'
        )

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_regenerate_recovery_codes_requires_recent_keycloak_auth_when_totp_set(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'cred', 'type': 'otp'}]

        response = self.client.post(reverse('api_regenerate_recovery_codes'))

        self.assertEqual(response.status_code, 403)
        self.mock_mfa_client.return_value.regenerate_recovery_codes.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_regenerate_recovery_codes_maps_totp_not_configured_to_conflict(self, mock_keycloak_client: Mock):
        # The provider rejects codes-only (re)generation: recovery codes are a backup
        # for the authenticator app, never a standalone factor.
        self.mock_mfa_client.return_value.regenerate_recovery_codes.side_effect = MfaCredentialError(
            MFA_REST_ERROR_TOTP_NOT_CONFIGURED
        )

        response = self.client.post(reverse('api_regenerate_recovery_codes'))

        self.assertEqual(response.status_code, 409)
        self.assertIn('authenticator app', response.json()['error'])

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_regenerate_recovery_codes_maps_session_expired_to_relogin(self, mock_keycloak_client: Mock):
        # A stale forwarded token on regenerate should prompt re-login (401), not 502.
        self.mock_mfa_client.return_value.regenerate_recovery_codes.side_effect = MfaSessionExpiredError()

        response = self.client.post(reverse('api_regenerate_recovery_codes'))

        self.assertEqual(response.status_code, 401)

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_regenerate_recovery_codes_maps_provider_step_up_to_reauth(self, mock_keycloak_client: Mock):
        # Backstop: the session pre-check passed (recent management auth) but the provider
        # rejected the forwarded token's claims — respond with the step-up redirect.
        self.mock_mfa_client.return_value.regenerate_recovery_codes.side_effect = MfaStepUpRequiredError()

        response = self.client.post(reverse('api_regenerate_recovery_codes'))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reauthUrl'], '/oidc/mfa-reauth/?next=%2Fmanage-mfa')

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
    def test_remove_recovery_codes_credential_checks_credential_belongs_to_user(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {'id': 'recovery-cred-id', 'type': 'recovery-authn-codes'}
        ]

        response = self.client.delete(reverse('api_remove_recovery_codes_credential', args=['recovery-cred-id']))

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.delete_credential.assert_called_once_with(
            'keycloak-user-id', 'recovery-cred-id'
        )

    @patch('thunderbird_accounts.authentication.mfa_management.KeycloakClient')
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
        client = KeycloakMfaClient()

        with patch.object(client, 'request') as mock_request:
            mock_request.return_value.json.return_value = _provider_setup_response()
            result = client.start_totp_setup(self.USER_TOKEN)

        endpoint, user_token, method = mock_request.call_args.args[:3]
        self.assertEqual(endpoint, 'totp/setup')
        self.assertEqual(user_token, self.USER_TOKEN)
        self.assertEqual(method, RequestMethods.GET)
        self.assertEqual(result, _provider_setup_response())

    def test_register_totp_credential_posts_secret_and_code(self):
        client = KeycloakMfaClient()

        with patch.object(client, 'request') as mock_request:
            mock_request.return_value.json.return_value = {'success': True, 'label': 'Authenticator app'}
            client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '123456', 'Authenticator app')

        endpoint, user_token, method = mock_request.call_args.args[:3]
        self.assertEqual(endpoint, 'totp/register')
        self.assertEqual(user_token, self.USER_TOKEN)
        self.assertEqual(method, RequestMethods.POST)
        # Enrollment-only: there is no overwrite flag in the provider contract.
        self.assertEqual(
            mock_request.call_args.kwargs['json_data'],
            {'secret': 'rawsecret', 'code': '123456', 'deviceName': 'Authenticator app'},
        )

    def test_register_totp_credential_raises_mfa_error_on_client_error(self):
        client = KeycloakMfaClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 400
        failing_response._content = json.dumps({'error': 'invalid_code'}).encode()

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(MfaCredentialError) as ctx:
                client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '000000', 'Authenticator app')

        self.assertEqual(ctx.exception.error_code, 'invalid_code')

    def test_register_totp_credential_raises_mfa_error_when_already_configured(self):
        client = KeycloakMfaClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 409
        failing_response._content = json.dumps({'error': MFA_REST_ERROR_ALREADY_CONFIGURED}).encode()

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(MfaCredentialError) as ctx:
                client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '123456', 'Authenticator app')

        self.assertEqual(ctx.exception.error_code, MFA_REST_ERROR_ALREADY_CONFIGURED)

    def test_regenerate_recovery_codes_raises_step_up_required(self):
        client = KeycloakMfaClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 401
        failing_response._content = json.dumps({'error': MFA_REST_ERROR_STEP_UP_REQUIRED}).encode()

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(MfaStepUpRequiredError):
                client.regenerate_recovery_codes(self.USER_TOKEN)

    def test_mfa_request_raises_session_expired_on_plain_unauthorized(self):
        # A 401 without the step_up_required marker is a plain auth failure (the forwarded
        # access token is missing/expired) — distinct from a step-up demand, and surfaced
        # as a re-login prompt rather than a generic upstream failure.
        client = KeycloakMfaClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 401
        failing_response._content = b''

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(MfaSessionExpiredError):
                client.regenerate_recovery_codes(self.USER_TOKEN)

    def test_register_totp_credential_reraises_upstream_errors(self):
        client = KeycloakMfaClient()
        failing_response = RequestsResponse()
        failing_response.status_code = 502

        with patch.object(client, 'request', side_effect=RequestException(response=failing_response)):
            with self.assertRaises(RequestException):
                client.register_totp_credential(self.USER_TOKEN, 'rawsecret', '000000', 'Authenticator app')

    def test_regenerate_recovery_codes_posts_to_provider(self):
        client = KeycloakMfaClient()

        with patch.object(client, 'request') as mock_request:
            mock_request.return_value.json.return_value = {'codes': ['AAAA', 'BBBB'], 'total': 2, 'remaining': 2}
            result = client.regenerate_recovery_codes(self.USER_TOKEN, user_label='Recovery codes')

        endpoint, user_token, method = mock_request.call_args.args[:3]
        self.assertEqual(endpoint, 'recovery-codes/regenerate')
        self.assertEqual(user_token, self.USER_TOKEN)
        self.assertEqual(method, RequestMethods.POST)
        self.assertEqual(mock_request.call_args.kwargs['json_data'], {'deviceName': 'Recovery codes'})
        self.assertEqual(result['codes'], ['AAAA', 'BBBB'])


class MfaReauthenticationRequestViewTestCase(TestCase):
    def test_step_up_redirect_requests_acr_only(self):
        params = MfaReauthenticationRequestView().get_extra_params(None)

        self.assertEqual(params['acr_values'], settings.MFA_KEYCLOAK_ACR_VALUE)
        # We must NOT send max_age: it would force a full re-authentication (first factor +
        # OTP). Freshness comes from the realm's L2 conditional-LoA (loa-max-age=0), which
        # re-challenges the OTP each step-up without re-prompting username/password.
        self.assertNotIn('max_age', params)


def _jwt_with_exp(exp_offset_seconds: int) -> str:
    """A JWT whose exp is `exp_offset_seconds` from now (signature is irrelevant — we only
    read exp without verifying)."""
    return jwt.encode(
        {'exp': int(time.time()) + exp_offset_seconds},
        'test-signing-key-not-verified-0123456789',
        algorithm='HS256',
    )


class GetUserAccessTokenTestCase(TestCase):
    """get_user_access_token forwards a live token, refreshing on demand when the stored one
    has expired so short-lived tokens don't get rejected by the mfa-rest provider."""

    @staticmethod
    def _request(**session):
        return SimpleNamespace(session=dict(session))

    @patch('thunderbird_accounts.authentication.mfa_management.refresh_user_access_token')
    def test_returns_unexpired_token_without_refreshing(self, mock_refresh: Mock):
        token = _jwt_with_exp(300)
        self.assertEqual(get_user_access_token(self._request(oidc_access_token=token)), token)
        mock_refresh.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.refresh_user_access_token', return_value='fresh-token')
    def test_refreshes_expired_token(self, mock_refresh: Mock):
        request = self._request(oidc_access_token=_jwt_with_exp(-10))
        self.assertEqual(get_user_access_token(request), 'fresh-token')
        mock_refresh.assert_called_once_with(request)

    @patch('thunderbird_accounts.authentication.mfa_management.refresh_user_access_token', return_value=None)
    def test_falls_back_to_stored_token_when_refresh_fails(self, _mock_refresh: Mock):
        expired = _jwt_with_exp(-10)
        self.assertEqual(get_user_access_token(self._request(oidc_access_token=expired)), expired)

    @patch('thunderbird_accounts.authentication.mfa_management.refresh_user_access_token')
    def test_opaque_token_is_forwarded_unchanged(self, mock_refresh: Mock):
        self.assertEqual(get_user_access_token(self._request(oidc_access_token='opaque-not-a-jwt')), 'opaque-not-a-jwt')
        mock_refresh.assert_not_called()

    @patch('thunderbird_accounts.authentication.mfa_management.refresh_user_access_token', return_value=None)
    def test_returns_none_when_no_token_stored(self, _mock_refresh: Mock):
        self.assertIsNone(get_user_access_token(self._request()))
