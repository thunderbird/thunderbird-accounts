import json
import time
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from requests import Response as RequestsResponse
from requests.exceptions import RequestException
from rest_framework.test import APIClient

from thunderbird_accounts.authentication.clients import KeycloakClient, RequestMethods
from thunderbird_accounts.authentication.mfa import (
    create_otpauth_uri,
    generate_recovery_codes,
    hash_recovery_code,
    make_pending_recovery_codes_cache_key,
    make_pending_totp_cache_key,
    make_totp_code,
    MFA_MANAGEMENT_AUTH_SESSION_KEY,
    RECOVERY_CODE_ALPHABET,
)
from thunderbird_accounts.authentication.models import User


class TotpTestCase(TestCase):
    @override_settings(MFA_TOTP_DIGITS=8, MFA_TOTP_PERIOD=30)
    def test_make_totp_code_uses_rfc6238_sha1_vectors(self):
        secret = '12345678901234567890'
        self.assertEqual(make_totp_code(secret, 59), '94287082')
        self.assertEqual(make_totp_code(secret, 1111111109), '07081804')
        self.assertEqual(make_totp_code(secret, 1111111111), '14050471')

    def test_create_otpauth_uri_matches_keycloak_policy(self):
        uri = create_otpauth_uri('abcdefghijklmnopqrst', 'test@example.com')
        self.assertIn('otpauth://totp/Thunderbird%20Accounts%3Atest%40example.com?', uri)
        self.assertIn('issuer=Thunderbird+Accounts', uri)
        self.assertIn('algorithm=SHA1', uri)
        self.assertIn('digits=6', uri)
        self.assertIn('period=30', uri)


class RecoveryCodesTestCase(TestCase):
    def test_generate_recovery_codes_uses_keycloak_alphabet_and_length(self):
        codes = generate_recovery_codes()

        self.assertEqual(len(codes), settings.MFA_RECOVERY_CODE_COUNT)
        for code in codes:
            self.assertEqual(len(code), settings.MFA_RECOVERY_CODE_LENGTH)
            self.assertTrue(set(code).issubset(set(RECOVERY_CODE_ALPHABET)))
        # Vanishingly unlikely to ever collide with a working alphabet,
        # but worth asserting we're getting fresh entropy on each code.
        self.assertEqual(len(set(codes)), len(codes))

    def test_hash_recovery_code_matches_keycloak_format(self):
        # Reference value: base64(SHA-512(utf8('ABCDEFGHJKLM'))). Matches
        # Keycloak's RecoveryAuthnCodesUtils#hashRawCode (SHA-512, base64, no salt).
        self.assertEqual(
            hash_recovery_code('ABCDEFGHJKLM'),
            'p+DMhIoz853kiiNUFbBrZwlDskNronzXZ6sjwawFZoDLeSxlPeAWy3h3KHkiJEWa'
            '+OtxAZ4qv0CY8+v2QRq2iA==',
        )


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

    def test_start_totp_setup_caches_secret_and_returns_otpauth_uri(self):
        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['otpAuthUri'].startswith('otpauth://totp/'))
        self.assertTrue(response_data['secret'])
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_totp_setup_validates_code_before_saving_credential(self, mock_keycloak_client: Mock):
        pending_secret = 'abcdefghijklmnopqrst'
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': pending_secret})
        mock_keycloak_client.return_value.replace_totp_credential.return_value = [
            {'id': 'new-credential-id', 'userLabel': 'Authenticator app'}
        ]

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': make_totp_code(pending_secret)},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.replace_totp_credential.assert_called_once_with(
            oidc_id='keycloak-user-id',
            secret=pending_secret,
            user_label='Authenticator app',
        )
        self.assertIsNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_totp_setup_rejects_invalid_code(self, mock_keycloak_client: Mock):
        cache.set(make_pending_totp_cache_key(self.user.pk), {'secret': 'abcdefghijklmnopqrst'})

        response = self.client.post(
            reverse('api_confirm_totp_setup'),
            data={'code': '000000'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        mock_keycloak_client.return_value.replace_totp_credential.assert_not_called()

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

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_totp_setup_allows_first_setup_without_keycloak_reauth(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = []

        response = self.client.post(reverse('api_start_totp_setup'))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(cache.get(make_pending_totp_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_recovery_codes_setup_caches_codes_without_writing_to_keycloak(self, mock_keycloak_client: Mock):
        response = self.client.post(reverse('api_start_recovery_codes_setup'))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body['codes']), settings.MFA_RECOVERY_CODE_COUNT)
        for code in body['codes']:
            self.assertEqual(len(code), settings.MFA_RECOVERY_CODE_LENGTH)
            self.assertTrue(set(code).issubset(set(RECOVERY_CODE_ALPHABET)))
        # Critical: existing recovery codes (if any) must remain valid until the user
        # acknowledges saving the new ones via the confirm endpoint.
        mock_keycloak_client.return_value.replace_recovery_codes_credential.assert_not_called()
        cached = cache.get(make_pending_recovery_codes_cache_key(self.user.pk))
        self.assertEqual(cached, {'codes': body['codes']})

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_start_recovery_codes_setup_requires_recent_keycloak_auth_when_totp_set(self, mock_keycloak_client: Mock):
        session = self.client.session
        session.pop(MFA_MANAGEMENT_AUTH_SESSION_KEY)
        session.save()
        mock_keycloak_client.return_value.get_totp_credentials.return_value = [{'id': 'cred', 'type': 'otp'}]

        response = self.client.post(reverse('api_start_recovery_codes_setup'))

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(cache.get(make_pending_recovery_codes_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_recovery_codes_setup_writes_cached_codes_to_keycloak(self, mock_keycloak_client: Mock):
        cached_codes = ['ABCDEFGHJKLM', 'ZYXWVUTSRQPN']
        cache.set(make_pending_recovery_codes_cache_key(self.user.pk), {'codes': cached_codes})
        mock_keycloak_client.return_value.replace_recovery_codes_credential.return_value = [
            {
                'id': 'recovery-cred-id',
                'type': 'recovery-authn-codes',
                'userLabel': 'Recovery codes',
                'credentialData': json.dumps({'algorithm': 'SHA-512', 'remaining': 2, 'total': 2}),
            }
        ]

        response = self.client.post(reverse('api_confirm_recovery_codes_setup'))

        self.assertEqual(response.status_code, 200)
        replace_call = mock_keycloak_client.return_value.replace_recovery_codes_credential
        replace_call.assert_called_once()
        self.assertEqual(replace_call.call_args.kwargs['raw_codes'], cached_codes)
        self.assertIsNone(cache.get(make_pending_recovery_codes_cache_key(self.user.pk)))

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_confirm_recovery_codes_setup_rejects_when_setup_expired(self, mock_keycloak_client: Mock):
        # No cache entry → setup expired (or never started).
        response = self.client.post(reverse('api_confirm_recovery_codes_setup'))

        self.assertEqual(response.status_code, 400)
        mock_keycloak_client.return_value.replace_recovery_codes_credential.assert_not_called()

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_remove_recovery_codes_credential_checks_credential_belongs_to_user(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {'id': 'recovery-cred-id', 'type': 'recovery-authn-codes'}
        ]

        response = self.client.delete(
            reverse('api_remove_recovery_codes_credential', args=['recovery-cred-id'])
        )

        self.assertEqual(response.status_code, 200)
        mock_keycloak_client.return_value.delete_credential.assert_called_once_with(
            'keycloak-user-id', 'recovery-cred-id'
        )

    @patch('thunderbird_accounts.authentication.api.KeycloakClient')
    def test_remove_recovery_codes_credential_rejects_unknown_credential(self, mock_keycloak_client: Mock):
        mock_keycloak_client.return_value.get_recovery_codes_credentials.return_value = [
            {'id': 'recovery-cred-id', 'type': 'recovery-authn-codes'}
        ]

        response = self.client.delete(
            reverse('api_remove_recovery_codes_credential', args=['some-other-id'])
        )

        self.assertEqual(response.status_code, 404)
        mock_keycloak_client.return_value.delete_credential.assert_not_called()


class KeycloakClientTotpTestCase(TestCase):
    @override_settings(MFA_TOTP_DIGITS=6, MFA_TOTP_PERIOD=30, MFA_TOTP_ALGORITHM='HmacSHA1')
    def test_create_totp_credential_sends_keycloak_otp_credential_representation(self):
        client = KeycloakClient()

        with (
            patch.object(client, 'get_user') as mock_get_user,
            patch.object(client, 'request') as mock_request,
            patch.object(client, 'get_totp_credentials', return_value=[]),
        ):
            mock_get_user.return_value.json.return_value = {'id': 'keycloak-user-id', 'username': 'test@example.com'}

            client.create_totp_credential('keycloak-user-id', 'abcdefghijklmnopqrst', 'Authenticator app')

        mock_request.assert_called_once()
        endpoint, method = mock_request.call_args.args[:2]
        self.assertEqual(endpoint, 'users/keycloak-user-id')
        self.assertEqual(method, RequestMethods.PUT)

        credential = mock_request.call_args.kwargs['json_data']['credentials'][0]
        self.assertEqual(credential['type'], 'otp')
        self.assertEqual(credential['userLabel'], 'Authenticator app')
        self.assertEqual(json.loads(credential['secretData']), {'value': 'abcdefghijklmnopqrst'})
        self.assertEqual(
            json.loads(credential['credentialData']),
            {
                'subType': 'totp',
                'digits': 6,
                'counter': 0,
                'period': 30,
                'algorithm': 'HmacSHA1',
            },
        )

    def test_replace_totp_credential_creates_new_before_deleting_existing(self):
        client = KeycloakClient()

        call_order: list[str] = []

        def fake_create(*args, **kwargs):
            call_order.append('create')

        def fake_delete(_oidc_id, credential_id):
            call_order.append(f'delete:{credential_id}')

        with (
            patch.object(client, 'get_totp_credentials', side_effect=[
                [{'id': 'old-1', 'type': 'otp'}, {'id': 'old-2', 'type': 'otp'}],
                [{'id': 'new', 'type': 'otp'}],
            ]),
            patch.object(client, 'create_totp_credential', side_effect=fake_create),
            patch.object(client, 'delete_credential', side_effect=fake_delete),
        ):
            client.replace_totp_credential('keycloak-user-id', 'secret', 'Authenticator app')

        self.assertEqual(call_order, ['create', 'delete:old-1', 'delete:old-2'])

    def test_replace_totp_credential_succeeds_when_old_delete_fails(self):
        client = KeycloakClient()

        failing_response = RequestsResponse()
        failing_response.status_code = 500
        delete_error = RequestException(response=failing_response)

        with (
            patch.object(client, 'get_totp_credentials', side_effect=[
                [{'id': 'old-1', 'type': 'otp'}],
                [{'id': 'old-1', 'type': 'otp'}, {'id': 'new', 'type': 'otp'}],
            ]),
            patch.object(client, 'create_totp_credential') as mock_create,
            patch.object(client, 'delete_credential', side_effect=delete_error),
            patch('thunderbird_accounts.authentication.clients.sentry_sdk.capture_exception') as mock_capture,
        ):
            credentials = client.replace_totp_credential('keycloak-user-id', 'secret', 'Authenticator app')

        mock_create.assert_called_once()
        mock_capture.assert_called_once_with(delete_error)
        self.assertEqual([credential['id'] for credential in credentials], ['old-1', 'new'])

    def test_create_recovery_codes_credential_sends_keycloak_credential_representation(self):
        client = KeycloakClient()
        raw_codes = ['ABCDEFGHJKLM', 'ZYXWVUTSRQPN']

        with (
            patch.object(client, 'get_user') as mock_get_user,
            patch.object(client, 'request') as mock_request,
            patch.object(client, 'get_recovery_codes_credentials', return_value=[]),
        ):
            mock_get_user.return_value.json.return_value = {'id': 'keycloak-user-id', 'username': 'test@example.com'}

            client.create_recovery_codes_credential('keycloak-user-id', raw_codes, 'Recovery codes')

        mock_request.assert_called_once()
        endpoint, method = mock_request.call_args.args[:2]
        self.assertEqual(endpoint, 'users/keycloak-user-id')
        self.assertEqual(method, RequestMethods.PUT)

        credential = mock_request.call_args.kwargs['json_data']['credentials'][0]
        self.assertEqual(credential['type'], 'recovery-authn-codes')
        self.assertEqual(credential['userLabel'], 'Recovery codes')
        self.assertEqual(
            json.loads(credential['credentialData']),
            {
                'hashIterations': None,
                'algorithm': settings.MFA_RECOVERY_CODE_ALGORITHM,
                'remaining': 2,
                'total': 2,
            },
        )
        secret_data = json.loads(credential['secretData'])
        self.assertEqual(len(secret_data['codes']), 2)
        for index, raw_code in enumerate(raw_codes):
            self.assertEqual(secret_data['codes'][index]['number'], index + 1)
            self.assertEqual(secret_data['codes'][index]['encodedHashedValue'], hash_recovery_code(raw_code))
