from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from thunderbird_accounts.authentication.clients import KeycloakClient, RequestMethods
from thunderbird_accounts.authentication.exceptions import RoleMappingError
from thunderbird_accounts.core.tests.utils import build_keycloak_success_response

OIDC_ID = 'd0e5c511-c78e-48be-a9ff-b7d3d8562ce4'
ROLE = {'id': 'role-uuid', 'name': 'thundermail-access'}


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    response._content = b'{"error":"boom"}'
    return requests.HTTPError(response=response)


@patch('thunderbird_accounts.authentication.clients.sentry_sdk.capture_exception')
@patch.object(KeycloakClient, 'request')
class KeycloakClientRealmRoleTestCase(SimpleTestCase):
    def test_get_realm_role_reads_role_by_url_encoded_name(self, mock_request, mock_capture):
        mock_request.return_value = build_keycloak_success_response(ROLE)

        self.assertEqual(KeycloakClient().get_realm_role('thundermail access/2'), ROLE)
        mock_request.assert_called_once_with('roles/thundermail%20access%2F2', RequestMethods.GET)
        mock_capture.assert_not_called()

    def test_get_realm_role_wraps_missing_role(self, mock_request, mock_capture):
        error = _http_error(404)
        mock_request.side_effect = error

        with self.assertRaises(RoleMappingError) as ctx:
            KeycloakClient().get_realm_role('thundermail-access')

        self.assertIs(ctx.exception.__cause__, error)
        self.assertEqual(ctx.exception.role_name, 'thundermail-access')
        self.assertIn('Error<404>', str(ctx.exception))
        mock_capture.assert_called_once_with(error)

    def test_grant_realm_role_posts_mapping_after_resolving_role(self, mock_request, mock_capture):
        mock_request.side_effect = [build_keycloak_success_response(ROLE), build_keycloak_success_response()]

        KeycloakClient().grant_realm_role(OIDC_ID, 'thundermail-access')

        mock_request.assert_any_call('roles/thundermail-access', RequestMethods.GET)
        mock_request.assert_called_with(
            f'users/{OIDC_ID}/role-mappings/realm',
            RequestMethods.POST,
            json_data=[{'id': 'role-uuid', 'name': 'thundermail-access'}],
        )

    def test_grant_realm_role_wraps_failure_with_user_and_cause(self, mock_request, mock_capture):
        error = requests.ConnectionError('keycloak unavailable')
        mock_request.side_effect = [build_keycloak_success_response(ROLE), error]

        with self.assertRaises(RoleMappingError) as ctx:
            KeycloakClient().grant_realm_role(OIDC_ID, 'thundermail-access')

        self.assertIs(ctx.exception.__cause__, error)
        self.assertEqual(ctx.exception.oidc_id, OIDC_ID)
        self.assertIn('No response!', str(ctx.exception))
        mock_capture.assert_called_once_with(error)

    def test_get_realm_role_member_ids_pages_until_a_short_page(self, mock_request, mock_capture):
        mock_request.side_effect = [
            build_keycloak_success_response([{'id': 'a'}, {'id': 'b'}]),
            build_keycloak_success_response([{'id': 'c'}]),
        ]

        members = KeycloakClient().get_realm_role_member_ids('thundermail-access', page_size=2)

        self.assertEqual(members, {'a', 'b', 'c'})
        self.assertEqual([call.kwargs['params']['first'] for call in mock_request.call_args_list], [0, 2])
        mock_request.assert_called_with(
            'roles/thundermail-access/users',
            RequestMethods.GET,
            params={'first': 2, 'max': 2, 'briefRepresentation': 'true'},
        )

    def test_get_client_default_scope_names(self, mock_request, mock_capture):
        mock_request.side_effect = [
            build_keycloak_success_response([{'id': 'client-uuid', 'clientId': 'tb-accounts'}]),
            build_keycloak_success_response([{'name': 'profile'}, {'name': 'pre-provisioning-login'}]),
            build_keycloak_success_response([]),
        ]
        client = KeycloakClient()

        self.assertEqual(client.get_client_default_scope_names('tb-accounts'), ['profile', 'pre-provisioning-login'])
        mock_request.assert_any_call('clients/client-uuid/default-client-scopes', RequestMethods.GET)
        self.assertIsNone(client.get_client_default_scope_names('missing'))


@patch('thunderbird_accounts.authentication.clients.requests.request')
@patch.object(KeycloakClient, '_get_access_token', side_effect=['token-1', 'token-2'])
class KeycloakClientTokenRefreshTestCase(SimpleTestCase):
    """An expired cached admin token is refreshed once and the request replayed."""

    def _response(self, status_code: int) -> requests.Response:
        response = requests.Response()
        response.status_code = status_code
        response._content = b'{}'
        return response

    def test_replays_once_after_401_on_a_cached_token(self, mock_get_token, mock_request):
        mock_request.side_effect = [self._response(200), self._response(401), self._response(200)]
        client = KeycloakClient()

        client.request('roles/x')
        client.request('roles/x')

        self.assertEqual(mock_get_token.call_count, 2)
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_request.call_args.kwargs['headers']['Authorization'], 'Bearer token-2')

    def test_does_not_replay_when_the_fresh_token_is_rejected(self, mock_get_token, mock_request):
        mock_request.side_effect = [self._response(401)]

        with self.assertRaises(requests.HTTPError):
            KeycloakClient().request('roles/x')

        self.assertEqual(mock_get_token.call_count, 1)
        self.assertEqual(mock_request.call_count, 1)
