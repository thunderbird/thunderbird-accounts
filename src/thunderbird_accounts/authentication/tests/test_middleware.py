from django.contrib.auth.models import AnonymousUser
import uuid
import datetime
from waffle.testutils import override_flag
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import freezegun
import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.forms import model_to_dict
from django.http import HttpRequest
from django.test import override_settings
from django.test import TestCase, RequestFactory


from thunderbird_accounts.authentication.middleware import (
    AccountsOIDCBackend,
    refresh_user_access_token,
    OIDCRefreshSession,
    EXIT_STATE_KEY, OIDC_ACCESS_TOKEN_KEY, OIDC_REFRESH_TOKEN_KEY, OIDC_ID_TOKEN_EXP_KEY,
)
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.models import AllowListEntry


@override_settings(
    OIDC_STORE_ACCESS_TOKEN=True,
    OIDC_STORE_REFRESH_TOKEN=True,
    OIDC_OP_TOKEN_ENDPOINT='https://keycloak.example/token',
    OIDC_RP_CLIENT_ID='client',
    OIDC_RP_CLIENT_SECRET='secret',
)
class RefreshUserAccessTokenTestCase(TestCase):
    @staticmethod
    def _request(**session):
        return SimpleNamespace(session=dict(session))

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    def test_refreshes_and_persists_rotated_tokens(self, mock_post: MagicMock):
        mock_post.return_value = MagicMock(
            json=MagicMock(return_value={'access_token': 'new-access', 'refresh_token': 'new-refresh'})
        )
        request = self._request(oidc_refresh_token='old-refresh')

        self.assertEqual(refresh_user_access_token(request), 'new-access')
        # The rotated pair is persisted so the next request reuses it.
        self.assertEqual(request.session['oidc_access_token'], 'new-access')
        self.assertEqual(request.session['oidc_refresh_token'], 'new-refresh')

    def test_returns_none_without_refresh_token(self):
        self.assertIsNone(refresh_user_access_token(self._request()))

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    def test_returns_none_when_provider_rejects_refresh(self, mock_post: MagicMock):
        # A dead SSO session yields a 400 from the token endpoint.
        mock_post.side_effect = requests.exceptions.HTTPError('400 Bad Request')
        self.assertIsNone(refresh_user_access_token(self._request(oidc_refresh_token='dead-refresh')))


@override_settings(
    OIDC_STORE_ACCESS_TOKEN=True,
    OIDC_STORE_REFRESH_TOKEN=True,
    OIDC_OP_TOKEN_ENDPOINT='https://keycloak.example/token',
    OIDC_RP_CLIENT_ID='client',
    OIDC_RP_CLIENT_SECRET='secret',
)
class OIDCRefreshSessionTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        get_response = MagicMock()
        self.middleware = OIDCRefreshSession(get_response)

        email = f'{uuid.uuid4()}@example.org'
        self.user = User.objects.create(username=f'{email}@example.org', email=f'{email}@example.org')
        self.anonymous_user = AnonymousUser()

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    @override_flag(settings.WAFFLE_FLAG_ALLOW_POST_REAUTH, False)
    @override_flag(settings.WAFFLE_FLAG_INTROSPECT_TOKEN_PER_REQUEST, False)
    def test_introspect_does_not_happen_without_feature_flag(self, mock_post: MagicMock):
        """This should hit the 'not expired' check and do nothing."""
        session = {
            OIDC_ID_TOKEN_EXP_KEY: (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp(),
            OIDC_ACCESS_TOKEN_KEY: 'abc123',
            OIDC_REFRESH_TOKEN_KEY: 'abc456',
        }

        mock_post.side_effect = AssertionError('request.post should not get called!')

        request = self.factory.get('/')
        request.session = session
        request.user = self.user
        resp = self.middleware.process_request(request)
        self.assertEqual(request.session.get(EXIT_STATE_KEY), OIDCRefreshSession.EXIT_STATES.NOT_EXPIRED)
        self.assertIsNone(resp)

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    @override_flag(settings.WAFFLE_FLAG_ALLOW_POST_REAUTH, False)
    @override_flag(settings.WAFFLE_FLAG_INTROSPECT_TOKEN_PER_REQUEST, True)
    def test_introspect_does_happen_if_feature_flag_is_set(self, mock_post: MagicMock):
        """This should hit a request.post, and our expected result for this test is the token is active."""
        session = {
            OIDC_ID_TOKEN_EXP_KEY: (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp(),
            OIDC_ACCESS_TOKEN_KEY: 'abc123',
            OIDC_REFRESH_TOKEN_KEY: 'abc456',
        }

        mock_post.return_value = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'active': True})

        request = self.factory.get('/')
        request.session = session
        request.user = self.user
        resp = self.middleware.process_request(request)
        self.assertEqual(request.session.get(EXIT_STATE_KEY), OIDCRefreshSession.EXIT_STATES.ACCESS_TOKEN_IS_ACTIVE)
        self.assertIsNone(resp)

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    @override_flag(settings.WAFFLE_FLAG_ALLOW_POST_REAUTH, False)
    @override_flag(settings.WAFFLE_FLAG_INTROSPECT_TOKEN_PER_REQUEST, True)
    def test_introspect_if_access_token_is_inactive(self, mock_post: MagicMock):
        """This should hit a request.post fail due to token being inactive, and refresh successfully."""
        session = {
            OIDC_ID_TOKEN_EXP_KEY: (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp(),
            OIDC_ACCESS_TOKEN_KEY: 'abc123',
            OIDC_REFRESH_TOKEN_KEY: 'abc456',
        }
        original_access_token = session.get(OIDC_ACCESS_TOKEN_KEY)

        mock_post.side_effect = [
            # Access token check
            SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'active': False}),
            # Refreshing access token
            SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {'access_token': 'abc789', 'refresh_token': session.get('oidc_refresh_token')},
            ),
        ]

        request = self.factory.get('/')
        request.session = session
        request.user = self.user
        self.middleware.process_request(request)
        self.assertEqual(request.session.get(EXIT_STATE_KEY), OIDCRefreshSession.EXIT_STATES.TOKEN_IS_STORED)
        self.assertNotEqual(request.session.get(OIDC_ACCESS_TOKEN_KEY), original_access_token)

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    @override_flag(settings.WAFFLE_FLAG_ALLOW_POST_REAUTH, False)
    @override_flag(settings.WAFFLE_FLAG_INTROSPECT_TOKEN_PER_REQUEST, False)
    def test_allow_post_reauth_does_not_happen_without_feature_flag(self, mock_post: MagicMock):
        """Try posting without this feature flag. It should set a "not refreshable" state."""
        session = {
            OIDC_ID_TOKEN_EXP_KEY: (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp(),
            OIDC_ACCESS_TOKEN_KEY: 'abc123',
            OIDC_REFRESH_TOKEN_KEY: 'abc456',
        }

        mock_post.side_effect = [
            # Access token check
            SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'active': False}),
            # Refreshing access token
            AssertionError('This request should not happen!')
        ]

        request = self.factory.post('/')
        request.session = session
        request.user = self.user
        resp = self.middleware.process_request(request)
        self.assertEqual(request.session.get(EXIT_STATE_KEY), OIDCRefreshSession.EXIT_STATES.NOT_REFRESHABLE)
        self.assertIsNone(resp)

    @patch('thunderbird_accounts.authentication.middleware.requests.post')
    @override_flag(settings.WAFFLE_FLAG_ALLOW_POST_REAUTH, True)
    @override_flag(settings.WAFFLE_FLAG_INTROSPECT_TOKEN_PER_REQUEST, False)
    def test_allow_post_reauth_does_happen_with_feature_flag(self, mock_post: MagicMock):
        """Try posting with this feature flag. It should mention it's not expired."""
        session = {
            OIDC_ID_TOKEN_EXP_KEY: (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp(),
            OIDC_ACCESS_TOKEN_KEY: 'abc123',
            OIDC_REFRESH_TOKEN_KEY: 'abc456',
        }

        mock_post.side_effect = [
            # Access token check
            SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'active': False}),
            # Refreshing access token
            SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {'access_token': 'abc789', 'refresh_token': session.get('oidc_refresh_token')},
            ),
        ]

        request = self.factory.post('/')
        request.session = session
        request.user = self.user
        resp = self.middleware.process_request(request)
        self.assertEqual(request.session.get(EXIT_STATE_KEY), OIDCRefreshSession.EXIT_STATES.NOT_EXPIRED)
        self.assertIsNone(resp)


@override_settings(USE_ALLOW_LIST=True)
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
        self.backend.request = HttpRequest()
        self.backend.request._messages = MagicMock()

        # Remove any allow list entries
        AllowListEntry.objects.all().delete()

    def test_create_user_success(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'zoneinfo': 'America/Vancouver',
            'email_verified': True,
            'name': 'Admin Example',
            'preferred_username': 'admin@example.org',
            'session_state': '196cb668-5492-4fd1-811b-72fdae44fd39',
            'given_name': 'Admin',
            'locale': 'en',
            'family_name': 'Example',
            'email': 'admin@example.com',
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = self.backend.create_user(claims)
        self.assertIsNotNone(user)

        self.assertEqual(user.email, claims.get('email'))
        self.assertEqual(user.username, claims.get('preferred_username'))
        self.assertEqual(user.display_name, claims.get('preferred_username'))
        self.assertEqual(user.get_full_name(), claims.get('name'))
        self.assertEqual(user.oidc_id, claims.get('sub'))
        self.assertEqual(user.language, claims.get('locale'))
        self.assertEqual(user.timezone, claims.get('zoneinfo'))

        # is_services_admin wasn't included in the claim, and the default create_user value is False
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_success_bare_minimum(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = self.backend.create_user(claims)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, claims.get('email'))
        self.assertEqual(user.username, claims.get('preferred_username'))
        self.assertEqual(user.display_name, claims.get('preferred_username'))
        self.assertEqual(user.oidc_id, claims.get('sub'))

    def test_create_user_fail_on_no_verified_email(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': False,
        }

        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)

    def test_create_user_fail_on_not_on_allow_list(self):
        # Just here to demonstrate that this user isn't on the allow list
        AllowListEntry.objects.create(email='admin@example.ca')
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': False,
        }

        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)

    def test_create_user_superuser_access(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
            'is_services_admin': 'yes',
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = self.backend.create_user(claims)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_update_user_success(self):
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
            # New data!
            'given_name': 'Example Admin',
            'is_services_admin': 'yes',
        }

        # Allow the user to sign-up
        AllowListEntry.objects.create(email=claims.get('email'))

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_staff=False,
            is_superuser=False,
        )
        # Retrieve a copy of the fields as update_user will update this instance.
        user_data = model_to_dict(user)

        user_updated = self.backend.update_user(user, claims)

        self.assertIsNotNone(user_updated)

        # Make sure these values are fixed
        self.assertFalse(user_data.get('is_staff'))
        self.assertFalse(user_data.get('is_superuser'))

        # Make sure nothing else has changed
        self.assertEqual(user_updated.email, user_data.get('email'))
        self.assertEqual(user_updated.username, user_data.get('username'))
        self.assertEqual(user_updated.display_name, user_data.get('display_name'))
        self.assertEqual(user_updated.oidc_id, user_data.get('oidc_id'))

        # Make sure these fields have changed
        self.assertNotEqual(user_updated.first_name, user_data.get('first_name'))
        self.assertNotEqual(user_updated.is_staff, user_data.get('is_staff'))
        self.assertNotEqual(user_updated.is_superuser, user_data.get('is_superuser'))

    def test_update_user_dont_reset_services_admin_permissions(self):
        """Testing update_user to make sure not including is_services_admin in claim will leave is_staff,
        and is_superuser fields alone."""
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@example.com',
            'email_verified': True,
        }

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_staff=True,
            is_superuser=True,
        )
        # Retrieve a copy of the fields as update_user will update this instance.
        user_data = model_to_dict(user)

        user_updated = self.backend.update_user(user, claims)

        self.assertIsNotNone(user_updated)

        # Make sure these values are fixed
        self.assertTrue(user_data.get('is_staff'))
        self.assertTrue(user_data.get('is_superuser'))

        # Make sure these fields have not changed
        self.assertTrue(user_updated.is_staff)
        self.assertTrue(user_updated.is_superuser)

    def test_update_active_user_doesnt_check_allowlist(self):
        """Testing update_user to make sure not including is_services_admin in claim will leave is_staff,
        and is_superuser fields alone."""
        settings.AUTH_ALLOW_LIST = 'example.org'
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@not_in_allow_list_example.com',
            'email_verified': True,
        }

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_active=True,
        )

        user_updated = self.backend.update_user(user, claims)
        self.assertIsNotNone(user_updated)
        settings.AUTH_ALLOW_LIST = ''

    def test_update_inactive_user_does_check_allowlist(self):
        """Testing update_user to make sure not including is_services_admin in claim will leave is_staff,
        and is_superuser fields alone."""
        claims = {
            'sub': '5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2',
            'preferred_username': 'admin@example.org',
            'email': 'admin@not_in_allow_list_example.com',
            'email_verified': True,
        }

        user = User.objects.create(
            email=claims.get('email'),
            username=claims.get('preferred_username'),
            display_name=claims.get('preferred_username'),
            oidc_id=claims.get('sub'),
            is_active=False,
        )

        with self.assertRaises(PermissionDenied):
            self.backend.update_user(user, claims)

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
