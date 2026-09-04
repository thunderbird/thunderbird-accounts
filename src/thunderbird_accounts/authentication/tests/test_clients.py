from unittest.mock import Mock, call, patch

from django.test import TestCase

from thunderbird_accounts.authentication.clients import KeycloakAccountClient, RequestMethods


class KeycloakAccountClientTestCase(TestCase):
    USER_TOKEN = 'user-access-token'

    def test_get_active_sessions_uses_online_sessions_with_device_details(self):
        client = KeycloakAccountClient()

        with patch.object(client, 'request') as mock_request:
            sessions_response = Mock()
            sessions_response.json.return_value = [
                {
                    'id': 'session-id',
                    'ipAddress': '203.0.113.11',
                    'started': 1710000000,
                    'lastAccess': 1710000000100,
                    'browser': 'Firefox',
                    'current': True,
                    'clients': [{'clientId': 'thunderbird-desktop', 'clientName': 'Thunderbird'}],
                }
            ]
            devices_response = Mock()
            devices_response.json.return_value = [
                {
                    'id': 'device-id',
                    'ipAddress': '203.0.113.10',
                    'lastAccess': 1710000000000,
                    'os': 'macOS',
                    'osVersion': '14.5',
                    'device': 'Mac',
                    'mobile': False,
                    'current': True,
                    'sessions': [
                        {
                            'id': 'session-id',
                            'ipAddress': '203.0.113.11',
                            'lastAccess': 1710000000100,
                            'current': True,
                            'clients': {'thunderbird-desktop': 'Thunderbird'},
                        }
                    ],
                }
            ]
            mock_request.side_effect = [sessions_response, devices_response]
            result = client.get_active_sessions(self.USER_TOKEN)

        self.assertEqual(
            mock_request.call_args_list,
            [
                call('account/sessions', self.USER_TOKEN, RequestMethods.GET),
                call('account/sessions/devices', self.USER_TOKEN, RequestMethods.GET),
            ],
        )
        self.assertEqual(
            result,
            [
                {
                    'id': 'session-id',
                    'access_given': 1710000000000,
                    'last_access': 1710000000100,
                    'ip_address': '203.0.113.11',
                    'device_info': {
                        'device': 'Mac',
                        'os': 'macOS',
                        'os_version': '14.5',
                        'browser': 'Firefox',
                        'app': 'Thunderbird',
                        'is_mobile': False,
                    },
                    'is_current': True,
                }
            ],
        )

    def test_get_active_sessions_excludes_offline_sessions_and_duplicate_device_entries(self):
        client = KeycloakAccountClient()

        with patch.object(client, 'request') as mock_request:
            sessions_response = Mock()
            sessions_response.json.return_value = [
                {
                    'id': 'online-session-id',
                    'ipAddress': '203.0.113.10',
                    'lastAccess': 1710000000200,
                    'browser': 'Firefox',
                    'clients': [{'clientId': 'tb-accounts', 'clientName': 'Thunderbird Accounts'}],
                }
            ]
            devices_response = Mock()
            devices_response.json.return_value = [
                {
                    'os': 'Linux',
                    'osVersion': '6.8',
                    'device': 'Other',
                    'mobile': False,
                    'sessions': [
                        {'id': 'online-session-id', 'lastAccess': 1710000000100},
                        {'id': 'online-session-id', 'lastAccess': 1710000000150},
                        {
                            'id': 'offline-session-id',
                            'lastAccess': 1710000000300,
                            'clients': [{'clientId': 'thunderbird-desktop', 'clientName': 'Thunderbird'}],
                        },
                    ],
                }
            ]
            mock_request.side_effect = [sessions_response, devices_response]

            result = client.get_active_sessions(self.USER_TOKEN)

        self.assertEqual([session['id'] for session in result], ['online-session-id'])
        self.assertEqual(result[0]['last_access'], 1710000000200)
        self.assertEqual(result[0]['device_info']['app'], 'Thunderbird Accounts')

    def test_get_connected_apps_returns_each_matching_session(self):
        client = KeycloakAccountClient()

        with patch.object(client, 'request') as mock_request:
            applications_response = Mock()
            applications_response.json.return_value = [
                {
                    'clientId': 'thunderbird-desktop',
                    'clientName': 'Mozilla Thunderbird',
                    'offlineAccess': True,
                    'consent': {'createdDate': 1700000000000},
                },
                {'clientId': 'tb-accounts', 'clientName': 'Thunderbird Accounts', 'offlineAccess': False},
            ]
            devices_response = Mock()
            devices_response.json.return_value = [
                {
                    'id': 'home-device',
                    'ipAddress': '203.0.113.10',
                    'lastAccess': 1710000000000,
                    'sessions': [
                        {
                            'id': 'home-session',
                            'started': 1710000000,
                            'clients': {'thunderbird-desktop': 'Thunderbird'},
                        }
                    ],
                },
                {
                    'id': 'work-device',
                    'sessions': [
                        {
                            'id': 'work-session',
                            'ipAddress': '203.0.113.11',
                            'lastAccess': 1710000000100,
                            'clients': [
                                {'clientId': 'thunderbird-desktop', 'clientName': 'Thunderbird'},
                                {'clientId': 'tb-accounts', 'clientName': 'Thunderbird Accounts'},
                            ],
                        }
                    ],
                },
            ]
            mock_request.side_effect = [applications_response, devices_response]

            result = client.get_connected_apps(self.USER_TOKEN)

        self.assertEqual(
            mock_request.call_args_list,
            [
                call('account/applications', self.USER_TOKEN, RequestMethods.GET),
                call('account/sessions/devices', self.USER_TOKEN, RequestMethods.GET),
            ],
        )
        self.assertEqual(
            result,
            [
                {
                    'client_id': 'thunderbird-desktop',
                    'session_id': 'home-session',
                    'app_name': 'Mozilla Thunderbird',
                    'access_given': 1710000000000,
                    'ip_address': '203.0.113.10',
                    'last_access': 1710000000000,
                },
                {
                    'client_id': 'thunderbird-desktop',
                    'session_id': 'work-session',
                    'app_name': 'Mozilla Thunderbird',
                    'access_given': 1700000000000,
                    'ip_address': '203.0.113.11',
                    'last_access': 1710000000100,
                },
            ],
        )

    def test_get_connected_apps_keeps_offline_app_without_device_metadata(self):
        client = KeycloakAccountClient()

        with patch.object(client, 'request') as mock_request:
            applications_response = Mock()
            applications_response.json.return_value = [
                {'clientId': 'one-password', 'clientName': '1Password', 'offlineAccess': True}
            ]
            devices_response = Mock()
            devices_response.json.return_value = []
            mock_request.side_effect = [applications_response, devices_response]

            result = client.get_connected_apps(self.USER_TOKEN)

        self.assertEqual(
            result,
            [{'client_id': 'one-password', 'app_name': '1Password', 'access_given': None}],
        )

    def test_revoke_connected_app_deletes_client_consent(self):
        client = KeycloakAccountClient()

        with patch.object(client, 'request') as mock_request:
            result = client.revoke_connected_app(self.USER_TOKEN, 'desktop/client')

        endpoint, user_token, method = mock_request.call_args.args[:3]
        self.assertEqual(endpoint, 'account/applications/desktop%2Fclient/consent')
        self.assertEqual(user_token, self.USER_TOKEN)
        self.assertEqual(method, RequestMethods.DELETE)
        self.assertEqual(result, {'success': True})

    def test_sign_out_session_deletes_account_session(self):
        client = KeycloakAccountClient()

        with patch.object(client, 'request') as mock_request:
            result = client.sign_out_session(self.USER_TOKEN, 'session-id')

        endpoint, user_token, method = mock_request.call_args.args[:3]
        self.assertEqual(endpoint, 'account/sessions/session-id')
        self.assertEqual(user_token, self.USER_TOKEN)
        self.assertEqual(method, RequestMethods.DELETE)
        self.assertEqual(result, {'success': True})
