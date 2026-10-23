import datetime
import time
from unittest.mock import Mock, patch

import jwt
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from requests import Response as RequestsResponse
from requests.exceptions import HTTPError, Timeout
from rest_framework.test import APIClient
from waffle.testutils import override_flag

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.app_passwords import (
    AppPasswordNameError,
    parse_app_password_name,
    serialize_app_password,
    visible_app_passwords,
)
from thunderbird_accounts.mail.exceptions import AppPasswordSetError, InvalidJMapResponseError
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.mail.types import stalwart
from thunderbird_accounts.subscription.models import Subscription

FLAG = settings.WAFFLE_FLAG_APP_PASSWORD_MANAGEMENT
CREATED_AT = datetime.datetime(2026, 10, 23, 4, 44, 55, tzinfo=datetime.timezone.utc)


def credential(pkid: str, description: str | None, created_at=CREATED_AT) -> stalwart.AppPassword:
    return stalwart.AppPassword(
        id=pkid,
        description=description,
        secret='$argon2id$hash-that-must-never-leak',
        created_at=created_at,
        permissions=stalwart.StalwartType(type='Inherit'),
        allowed_ips={},
    )


class AppPasswordHelpersTestCase(SimpleTestCase):
    def test_serialize_app_password_only_exposes_metadata(self):
        data = serialize_app_password(credential('abc', 'Laptop'))

        self.assertEqual(data, {'id': 'abc', 'name': 'Laptop', 'createdAt': '2026-10-23T04:44:55+00:00'})
        self.assertNotIn('secret', data)

    def test_serialize_app_password_tolerates_missing_name_and_date(self):
        self.assertEqual(
            serialize_app_password(credential('abc', None, created_at=None)),
            {'id': 'abc', 'name': '', 'createdAt': None},
        )

    def test_visible_app_passwords_hides_internal_and_idless_credentials(self):
        appointment = f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}user@example.org'
        visible = visible_app_passwords(
            [
                credential('a', 'Laptop'),
                credential('b', appointment),
                credential('c', appointment.upper()),
                credential('d', 'Thunderbird QR setup'),
                credential(None, 'no id'),
                credential('e', None),
            ]
        )

        self.assertEqual([c.id for c in visible], ['a', 'd', 'e'])

    def test_parse_app_password_name_strips_and_returns_valid_names(self):
        self.assertEqual(parse_app_password_name({'name': '  Phone  '}), 'Phone')

    def test_parse_app_password_name_rejects_bad_shapes_and_values(self):
        too_long = 'x' * (settings.APP_PASSWORD_NAME_MAX_LENGTH + 1)
        for payload in (
            ['Phone'],
            'Phone',
            {},
            {'name': None},
            {'name': 42},
            {'name': ''},
            {'name': '   '},
            {'name': too_long},
            {'name': 'tab\tname'},
            {'name': f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}anything'},
            {'name': settings.APPOINTMENT_APP_PASSWORD_PREFIX.upper() + 'x'},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(AppPasswordNameError) as raised:
                    parse_app_password_name(payload)
                self.assertTrue(raised.exception.message)


@override_settings(STALWART_ADMIN_API_USE_JMAP=True)
@override_flag(FLAG, active=True)
@patch('thunderbird_accounts.mail.app_passwords.MailClientUserJMAP')
class AppPasswordManagementApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.primary_email = f'manager@{settings.PRIMARY_EMAIL_DOMAIN}'
        self.user = User.objects.create(username=self.primary_email, email='signin@example.com', oidc_id='mgr-1')
        # verified_archive_folder keeps the archive-folder middleware from opening a real JMAP session per request.
        self.account = Account.objects.create(name=self.primary_email, user=self.user, verified_archive_folder=True)
        Email.objects.create(address=self.primary_email, type=Email.EmailType.PRIMARY, account=self.account)
        self.subscription = Subscription.objects.create(user=self.user, status=Subscription.StatusValues.ACTIVE)
        self.client.force_login(self.user)
        self._set_access_token('user-access-token')

        self.list_url = reverse('api_app_password_list')
        self.create_url = reverse('api_app_password_create')
        self.appointment_label = f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}{self.primary_email}'

    def _set_access_token(self, token):
        session = self.client.session
        if token is None:
            session.pop('oidc_access_token', None)
        else:
            session['oidc_access_token'] = token
        session.save()

    def _revoke_url(self, pkid):
        return reverse('api_app_password_revoke', kwargs={'app_password_id': pkid})

    def _client(self, mock_cls, credentials=None):
        jmap_client = Mock()
        jmap_client.get_app_passwords.return_value = credentials if credentials is not None else []
        mock_cls.return_value = jmap_client
        return jmap_client

    # Listing

    def test_list_returns_sanitized_metadata_without_internal_credentials(self, mock_cls):
        jmap_client = self._client(
            mock_cls,
            [
                credential('a', 'Laptop'),
                credential('b', self.appointment_label),
                credential('c', None, created_at=None),
                credential('d', 'Thunderbird Mobile (QR)'),
            ],
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['Cache-Control'].split(', ')[0], 'max-age=0')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(
            response.json(),
            {
                'success': True,
                'username': self.primary_email,
                'appPasswords': [
                    {'id': 'a', 'name': 'Laptop', 'createdAt': '2026-10-23T04:44:55+00:00'},
                    {'id': 'c', 'name': '', 'createdAt': None},
                    {'id': 'd', 'name': 'Thunderbird Mobile (QR)', 'createdAt': '2026-10-23T04:44:55+00:00'},
                ],
            },
        )
        self.assertNotIn('hash-that-must-never-leak', response.content.decode())
        mock_cls.assert_called_once_with(self.primary_email, 'user-access-token')
        jmap_client.delete_app_password.assert_not_called()

    def test_list_reports_stalwart_failures_as_bad_gateway(self, mock_cls):
        for failure in (AppPasswordSetError('serverFail', 'boom', None), RuntimeError('empty response')):
            with self.subTest(failure=type(failure).__name__):
                self._client(mock_cls).get_app_passwords.side_effect = failure

                response = self.client.get(self.list_url)

                self.assertEqual(response.status_code, 502)
                self.assertFalse(response.json()['success'])

    def test_list_reports_a_failed_jmap_session_as_bad_gateway(self, mock_cls):
        mock_cls.side_effect = InvalidJMapResponseError(None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 502)

    # Gates shared by every management route

    def test_routes_are_hidden_while_the_flag_is_off(self, mock_cls):
        with override_flag(FLAG, active=False):
            responses = [
                self.client.get(self.list_url),
                self.client.post(self.create_url, {'name': 'Laptop'}, format='json'),
                self.client.delete(self._revoke_url('a')),
            ]

        for response in responses:
            self.assertEqual(response.status_code, 404, response.content)
            self.assertEqual(response.json(), {'success': False, 'error': 'Not found'})
        mock_cls.assert_not_called()

    @override_settings(STALWART_ADMIN_API_USE_JMAP=False)
    def test_routes_are_hidden_on_the_legacy_admin_api(self, mock_cls):
        self.assertEqual(self.client.get(self.list_url).status_code, 404)
        self.assertEqual(self.client.post(self.create_url, {'name': 'Laptop'}, format='json').status_code, 404)
        mock_cls.assert_not_called()

    def test_routes_require_authentication(self, mock_cls):
        self.client.logout()

        self.assertIn(self.client.get(self.list_url).status_code, (401, 403))
        self.assertIn(self.client.post(self.create_url, {'name': 'Laptop'}, format='json').status_code, (401, 403))
        self.assertIn(self.client.delete(self._revoke_url('a')).status_code, (401, 403))
        mock_cls.assert_not_called()

    def test_routes_require_an_active_subscription(self, mock_cls):
        self.subscription.status = Subscription.StatusValues.CANCELED
        self.subscription.save()

        response = self.client.post(self.create_url, {'name': 'Laptop'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        mock_cls.assert_not_called()

    def test_mutations_are_csrf_protected(self, mock_cls):
        strict_client = APIClient(enforce_csrf_checks=True)
        strict_client.force_login(self.user)
        session = strict_client.session
        session['oidc_access_token'] = 'user-access-token'
        session.save()

        self.assertEqual(strict_client.post(self.create_url, {'name': 'Laptop'}, format='json').status_code, 403)
        self.assertEqual(strict_client.delete(self._revoke_url('a')).status_code, 403)
        mock_cls.assert_not_called()

    def test_routes_answer_conflict_until_the_mailbox_exists(self, mock_cls):
        self.account.delete()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'mail_account_not_ready')
        mock_cls.assert_not_called()

    def test_routes_answer_unauthorized_without_an_access_token(self, mock_cls):
        self._set_access_token(None)

        response = self.client.post(self.create_url, {'name': 'Laptop'}, format='json')

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()['success'])
        mock_cls.assert_not_called()

    def test_routes_refresh_expired_access_tokens_before_opening_jmap(self, mock_cls):
        expired_token = jwt.encode(
            {'exp': int(time.time()) - 10},
            'test-signing-key-not-verified-0123456789',
            algorithm='HS256',
        )
        requests = (
            ('GET', lambda: self.client.get(self.list_url)),
            ('POST', lambda: self.client.post(self.create_url, {'name': 'Phone'}, format='json')),
            ('DELETE', lambda: self.client.delete(self._revoke_url('a'))),
        )

        for method, send_request in requests:
            with self.subTest(method=method):
                self._set_access_token(expired_token)
                mock_cls.reset_mock()
                jmap_client = self._client(mock_cls, [credential('a', 'Laptop')])
                jmap_client.save_app_password.return_value = Mock(id='new', secret='generated-secret')

                with patch(
                    'thunderbird_accounts.authentication.middleware.refresh_user_access_token',
                    return_value='refreshed-access-token',
                ) as refresh:
                    response = send_request()

                self.assertEqual(response.status_code, 200, response.content)
                refresh.assert_called_once()
                mock_cls.assert_called_once_with(self.primary_email, 'refreshed-access-token')
                if method == 'POST':
                    jmap_client.save_app_password.assert_called_once_with('Phone')
                else:
                    jmap_client.save_app_password.assert_not_called()
                if method == 'DELETE':
                    jmap_client.delete_app_password.assert_called_once_with('a')
                else:
                    jmap_client.delete_app_password.assert_not_called()

    def test_failed_refresh_and_jmap_unauthorized_report_session_expiry(self, mock_cls):
        expired_token = jwt.encode(
            {'exp': int(time.time()) - 10},
            'test-signing-key-not-verified-0123456789',
            algorithm='HS256',
        )
        self._set_access_token(expired_token)
        provider_response = RequestsResponse()
        provider_response.status_code = 401
        jmap_client = self._client(mock_cls)
        mock_cls.side_effect = HTTPError(response=provider_response)

        with patch(
            'thunderbird_accounts.authentication.middleware.refresh_user_access_token', return_value=None
        ) as refresh:
            response = self.client.post(self.create_url, {'name': 'Phone'}, format='json')

        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(
            response.json(), {'success': False, 'error': 'Your session has expired. Please sign in again.'}
        )
        refresh.assert_called_once()
        mock_cls.assert_called_once_with(self.primary_email, expired_token)
        jmap_client.save_app_password.assert_not_called()

    def test_jmap_connection_failures_remain_bad_gateway(self, mock_cls):
        provider_response = RequestsResponse()
        provider_response.status_code = 503
        for failure in (HTTPError(response=provider_response), Timeout('Timed out')):
            with self.subTest(failure=type(failure).__name__):
                mock_cls.side_effect = failure

                response = self.client.get(self.list_url)

                self.assertEqual(response.status_code, 502, response.content)
                self.assertEqual(
                    response.json(),
                    {'success': False, 'error': 'Could not connect to Thundermail, please try again later.'},
                )

    def test_operation_errors_distinguish_expired_sessions_from_service_failures(self, mock_cls):
        operations = (
            (
                'list',
                'get_app_passwords',
                lambda: self.client.get(self.list_url),
                'Could not load your app passwords, please try again later.',
            ),
            (
                'create',
                'save_app_password',
                lambda: self.client.post(self.create_url, {'name': 'Phone'}, format='json'),
                'Could not create the app password, please try again later.',
            ),
            (
                'remove lookup',
                'get_app_passwords',
                lambda: self.client.delete(self._revoke_url('a')),
                'Could not remove the app password, please try again later.',
            ),
            (
                'remove',
                'delete_app_password',
                lambda: self.client.delete(self._revoke_url('a')),
                'Could not remove the app password, please try again later.',
            ),
        )

        for provider_status in (401, 503):
            for operation, method, send_request, fallback_message in operations:
                with self.subTest(provider_status=provider_status, operation=operation):
                    jmap_client = self._client(mock_cls, [credential('a', 'Laptop')])
                    provider_response = RequestsResponse()
                    provider_response.status_code = provider_status
                    getattr(jmap_client, method).side_effect = HTTPError(response=provider_response)

                    with patch('thunderbird_accounts.mail.app_passwords.sentry_sdk.capture_exception') as capture:
                        response = send_request()

                    expired = provider_status == 401
                    self.assertEqual(response.status_code, 401 if expired else 502, response.content)
                    self.assertEqual(
                        response.json(),
                        {
                            'success': False,
                            'error': 'Your session has expired. Please sign in again.' if expired else fallback_message,
                        },
                    )
                    self.assertIn('no-store', response['Cache-Control'])
                    getattr(jmap_client, method).assert_called_once()
                    if method != 'delete_app_password':
                        jmap_client.delete_app_password.assert_not_called()
                    if expired:
                        capture.assert_not_called()
                    else:
                        capture.assert_called_once()

    # Creation

    def test_create_adds_a_named_password_without_touching_existing_ones(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('old', 'Laptop'), credential('new', 'Laptop')])
        jmap_client.save_app_password.return_value = Mock(id='new', secret='generated-secret')

        response = self.client.post(self.create_url, {'name': '  Laptop  '}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(
            response.json(),
            {
                'success': True,
                'appPassword': {'id': 'new', 'name': 'Laptop', 'createdAt': '2026-10-23T04:44:55+00:00'},
                'secret': 'generated-secret',
                'username': self.primary_email,
            },
        )
        jmap_client.save_app_password.assert_called_once_with('Laptop')
        jmap_client.delete_app_password.assert_not_called()
        jmap_client.replace_app_password.assert_not_called()

    def test_create_keeps_the_secret_when_the_metadata_reload_fails(self, mock_cls):
        provider_response = RequestsResponse()
        provider_response.status_code = 401
        for failure in (
            RuntimeError('Stalwart JMAP response did not include x:AppPassword/get'),
            ValueError('x'),
            HTTPError(response=provider_response),
        ):
            with self.subTest(failure=type(failure).__name__):
                jmap_client = self._client(mock_cls)
                jmap_client.save_app_password.return_value = Mock(id='new', secret='generated-secret')
                jmap_client.get_app_passwords.side_effect = failure

                response = self.client.post(self.create_url, {'name': 'Phone'}, format='json')

                self.assertEqual(response.status_code, 200, response.content)
                payload = response.json()
                self.assertEqual(payload['secret'], 'generated-secret')
                self.assertEqual(payload['appPassword'], {'id': 'new', 'name': 'Phone', 'createdAt': None})

    def test_create_validates_the_name(self, mock_cls):
        jmap_client = self._client(mock_cls)
        for payload in (
            {},
            {'name': ''},
            {'name': '   '},
            {'name': 5},
            {'name': 'x' * (settings.APP_PASSWORD_NAME_MAX_LENGTH + 1)},
            {'name': f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}sneaky'},
            ['Laptop'],
        ):
            with self.subTest(payload=payload):
                response = self.client.post(self.create_url, payload, format='json')

                self.assertEqual(response.status_code, 400, response.content)
                self.assertFalse(response.json()['success'])
                self.assertTrue(response.json()['error'])
        jmap_client.save_app_password.assert_not_called()

    def test_create_rejects_malformed_json(self, mock_cls):
        jmap_client = self._client(mock_cls)

        response = self.client.post(self.create_url, 'not json', content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'success': False, 'error': 'Invalid request data'})
        jmap_client.save_app_password.assert_not_called()

    def test_create_reports_quota_without_deleting_anything(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('old', 'Laptop')])
        jmap_client.save_app_password.side_effect = AppPasswordSetError(
            'overQuota', 'You have exceeded your quota of 5 app passwords.', None
        )

        response = self.client.post(self.create_url, {'name': 'Laptop'}, format='json')

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'app_password_quota')
        self.assertNotIn('secret', response.json())
        jmap_client.delete_app_password.assert_not_called()

    def test_create_reports_other_stalwart_failures_as_bad_gateway(self, mock_cls):
        for failure in (AppPasswordSetError('forbidden', 'nope', None), InvalidJMapResponseError(None)):
            with self.subTest(failure=type(failure).__name__):
                self._client(mock_cls).save_app_password.side_effect = failure

                response = self.client.post(self.create_url, {'name': 'Laptop'}, format='json')

                self.assertEqual(response.status_code, 502, response.content)
                self.assertFalse(response.json()['success'])

    # Revocation

    def test_revoke_deletes_exactly_the_requested_credential(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('a', 'Laptop'), credential('b', 'Phone')])

        response = self.client.delete(self._revoke_url('b'))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'success': True, 'id': 'b'})
        self.assertIn('no-store', response['Cache-Control'])
        jmap_client.delete_app_password.assert_called_once_with('b')

    def test_revoke_rejects_ids_the_user_does_not_own(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('a', 'Laptop')])

        response = self.client.delete(self._revoke_url('someone-elses-id'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {'success': False, 'error': 'App password not found.', 'code': 'app_password_not_found'},
        )
        jmap_client.delete_app_password.assert_not_called()

    def test_revoke_refuses_hidden_appointment_credentials(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('a', 'Laptop'), credential('b', self.appointment_label)])

        response = self.client.delete(self._revoke_url('b'))

        self.assertEqual(response.status_code, 404)
        # No "already gone" code: a crafted request must not be able to make the UI drop a row as revoked.
        self.assertEqual(response.json(), {'success': False, 'error': 'App password not found.'})
        jmap_client.delete_app_password.assert_not_called()

    def test_revoke_is_idempotent_when_stalwart_already_dropped_it(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('a', 'Laptop')])
        jmap_client.delete_app_password.side_effect = AppPasswordSetError('notFound', None, None)

        response = self.client.delete(self._revoke_url('a'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'app_password_not_found')

    def test_revoke_reports_other_failures_as_bad_gateway(self, mock_cls):
        for failure in (
            AppPasswordSetError('forbidden', 'nope', None),
            ValueError('Response does not include every requested app password id'),
        ):
            with self.subTest(failure=type(failure).__name__):
                self._client(mock_cls, [credential('a', 'Laptop')]).delete_app_password.side_effect = failure

                response = self.client.delete(self._revoke_url('a'))

                self.assertEqual(response.status_code, 502, response.content)
                self.assertFalse(response.json()['success'])

    def test_revoke_only_accepts_delete(self, mock_cls):
        jmap_client = self._client(mock_cls, [credential('a', 'Laptop')])

        self.assertEqual(self.client.post(self._revoke_url('a')).status_code, 405)
        self.assertEqual(self.client.get(self._revoke_url('a')).status_code, 405)
        jmap_client.delete_app_password.assert_not_called()
