import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import freezegun
import requests
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.forms import model_to_dict
from django.http import HttpRequest, JsonResponse
from django.test import override_settings
from django.test import Client as RequestClient, SimpleTestCase, TestCase
from django.urls import path, resolve, reverse


from thunderbird_accounts.authentication.middleware import (
    AccountsOIDCBackend,
    RequiredAuth,
    refresh_user_access_token,
)
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.models import AllowListEntry
from thunderbird_accounts.core.tests.utils import oidc_force_login
from thunderbird_accounts.subscription.models import Subscription
from thunderbird_accounts.urls import authorized_path


def authorization_test_view(request, **kwargs):
    return JsonResponse({'kwargs': kwargs})


authorization_test_urlpatterns = [
    path('view/', authorization_test_view, name='authorization_test_view'),
]

urlpatterns = [
    authorized_path(
        'auth/',
        authorization_test_urlpatterns,
        required_auth=RequiredAuth.AUTHENTICATED,
    ),
    authorized_path(
        'subscribed/',
        authorization_test_urlpatterns,
        required_auth=RequiredAuth.ACTIVE_SUBSCRIPTION,
    ),
    authorized_path(
        'subscribed-empty-response/',
        authorization_test_urlpatterns,
        required_auth=RequiredAuth.ACTIVE_SUBSCRIPTION,
        active_subscription_response_data={},
        active_subscription_status=401,
    ),
    authorized_path(
        'subscribed-custom-error/',
        authorization_test_urlpatterns,
        required_auth=RequiredAuth.ACTIVE_SUBSCRIPTION,
        active_subscription_error_message='No active subscription found',
        active_subscription_status=404,
    ),
    authorized_path(
        'admin-only/',
        authorization_test_urlpatterns,
        required_auth=RequiredAuth.ADMIN,
    ),
    path('django-admin/', admin.site.urls),
    path('login/', authorization_test_view, name='authorization_test_login'),
]

AUTHORIZATION_TEST_MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'thunderbird_accounts.authentication.middleware.AuthorizationMiddleware',
]

ADMIN_ROUTE_CASES = [
    ('allow_list_entry_import', 'get', {}),
    ('allow_list_entry_import_submit', 'post', {'bulk-entry': 'user@example.com'}),
    ('admin_stalwart_list', 'get', {}),
]

AUTHENTICATED_ROUTE_CASES = [
    ('legal_current', 'get', {}),
    ('legal_accept', 'post', {}),
    ('legal_decline', 'post', {}),
    ('paddle_completed', 'get', {}),
    ('paddle_info', 'post', {}),
    ('paddle_txid', 'put', {'txid': 'tx_123'}),
    ('paddle_is_done', 'post', {}),
]

ACTIVE_SUBSCRIPTION_ROUTE_CASES = [
    ('app_password_set', 'post', {'name': 'Primary account', 'password': 'new-password'}),
    ('display_name_set', 'post', {'display-name': 'New Name'}),
    ('add_custom_domain', 'post', {'domain-name': 'example.com'}),
    ('get_dns_records', 'get', {'domain-name': 'example.com'}),
    ('verify_custom_domain', 'post', {'domain-name': 'example.com'}),
    ('remove_custom_domain', 'delete', {'domain-name': 'example.com'}),
    ('add_email_alias', 'post', {'email-alias': 'buddy', 'domain': settings.PRIMARY_EMAIL_DOMAIN}),
    ('remove_email_alias', 'delete', {'email-alias': f'buddy@{settings.PRIMARY_EMAIL_DOMAIN}'}),
    ('api_app_password_set', 'post', {'name': 'Primary account', 'password': 'new-password'}),
    ('api_display_name_set', 'post', {'display-name': 'New Name'}),
    ('paddle_portal', 'post', {}),
    ('subscription_plan_info', 'post', {}),
]

if settings.AUTH_SCHEME == 'oidc':
    AUTHENTICATED_ROUTE_CASES += [
        ('mfa_reauth', 'get', {}),
        ('logout_callback', 'get', {}),
        ('reset_password', 'get', {}),
    ]
    ACTIVE_SUBSCRIPTION_ROUTE_CASES.append(('jmap-test', 'get', {}))


@override_settings(
    ROOT_URLCONF='thunderbird_accounts.authentication.tests.test_middleware',
    MIDDLEWARE=AUTHORIZATION_TEST_MIDDLEWARE,
    LOGIN_URL='/login/',
)
class AuthorizationMiddlewareTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()

    def test_authenticated_include_requires_login_and_strips_metadata(self):
        response = self.client.get('/auth/view/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/login/?next=/auth/view/')

        user = User.objects.create(username=f'auth@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='auth')
        oidc_force_login(self.client, user)

        response = self.client.get('/auth/view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'kwargs': {}})

    def test_active_subscription_include_requires_active_subscription(self):
        user = User.objects.create(username=f'subscriber@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='subscriber')
        oidc_force_login(self.client, user)

        response = self.client.get('/subscribed/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {'success': False, 'error': 'An active subscription is required.'})

        Subscription.objects.create(user=user, status=Subscription.StatusValues.ACTIVE)

        response = self.client.get('/subscribed/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'kwargs': {}})

    def test_active_subscription_include_supports_custom_error_response(self):
        user = User.objects.create(username=f'custom@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='custom')
        oidc_force_login(self.client, user)

        response = self.client.get('/subscribed-empty-response/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {})

        response = self.client.get('/subscribed-custom-error/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'success': False, 'error': 'No active subscription found'})

    def test_admin_include_requires_staff(self):
        user = User.objects.create(username=f'user@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='user')
        oidc_force_login(self.client, user)

        response = self.client.get('/admin-only/view/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/django-admin/login/?next=/admin-only/view/')

        staff_user = User.objects.create(
            username=f'staff@{settings.PRIMARY_EMAIL_DOMAIN}',
            oidc_id='staff',
            is_staff=True,
        )
        oidc_force_login(self.client, staff_user)

        response = self.client.get('/admin-only/view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'kwargs': {}})


@override_settings(MIDDLEWARE=AUTHORIZATION_TEST_MIDDLEWARE, LOGIN_URL='/login/')
class AuthorizationProtectedRouteTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()

    def _request(self, route_case):
        url_name, method, data = route_case
        url = reverse(url_name)

        if method == 'get':
            return self.client.get(url, data=data, HTTP_ACCEPT='application/json')

        return getattr(self.client, method)(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_ACCEPT='application/json',
        )

    def test_authenticated_routes_redirect_anonymous_users_to_login(self):
        for route_case in AUTHENTICATED_ROUTE_CASES:
            with self.subTest(url_name=route_case[0]):
                response = self._request(route_case)

                self.assertEqual(response.status_code, 302)
                self.assertIn('next=', response['Location'])

    def test_active_subscription_routes_reject_users_without_active_subscriptions(self):
        user = User.objects.create(username=f'no-subscription@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='no-sub')
        oidc_force_login(self.client, user)
        custom_denials = {
            'paddle_portal': (401, {}),
            'subscription_plan_info': (404, {'success': False, 'error': 'No active subscription found'}),
        }

        for route_case in ACTIVE_SUBSCRIPTION_ROUTE_CASES:
            url_name = route_case[0]
            with self.subTest(url_name=url_name):
                response = self._request(route_case)
                expected_status, expected_json = custom_denials.get(
                    url_name,
                    (403, {'success': False, 'error': 'An active subscription is required.'}),
                )

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json(), expected_json)

    def test_admin_routes_redirect_non_staff_users_to_admin_login(self):
        user = User.objects.create(username=f'not-staff@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='not-staff')
        oidc_force_login(self.client, user)

        for route_case in ADMIN_ROUTE_CASES:
            with self.subTest(url_name=route_case[0]):
                response = self._request(route_case)

                self.assertEqual(response.status_code, 302)
                self.assertIn('/admin/login/', response['Location'])


class AuthorizationUrlMetadataTestCase(SimpleTestCase):
    def test_root_urlconf_marks_admin_route_groups(self):
        for url_name, _, _ in ADMIN_ROUTE_CASES:
            with self.subTest(url_name=url_name):
                self.assertEqual(
                    resolve(reverse(url_name)).extra_kwargs.get('required_auth'),
                    RequiredAuth.ADMIN,
                )

    def test_root_urlconf_marks_authenticated_route_groups(self):
        for url_name, _, _ in AUTHENTICATED_ROUTE_CASES:
            with self.subTest(url_name=url_name):
                self.assertEqual(
                    resolve(reverse(url_name)).extra_kwargs.get('required_auth'),
                    RequiredAuth.AUTHENTICATED,
                )

    def test_root_urlconf_marks_active_subscription_route_groups(self):
        for url_name, _, _ in ACTIVE_SUBSCRIPTION_ROUTE_CASES:
            with self.subTest(url_name=url_name):
                self.assertEqual(
                    resolve(reverse(url_name)).extra_kwargs.get('required_auth'),
                    RequiredAuth.ACTIVE_SUBSCRIPTION,
                )

    def test_root_urlconf_marks_active_subscription_custom_denials(self):
        self.assertEqual(resolve(reverse('paddle_portal')).extra_kwargs.get('active_subscription_response_data'), {})
        self.assertEqual(resolve(reverse('paddle_portal')).extra_kwargs.get('active_subscription_status'), 401)
        self.assertEqual(
            resolve(reverse('subscription_plan_info')).extra_kwargs.get('active_subscription_error_message'),
            'No active subscription found',
        )
        self.assertEqual(
            resolve(reverse('subscription_plan_info')).extra_kwargs.get('active_subscription_status'),
            404,
        )

    def test_root_urlconf_leaves_non_session_auth_routes_unmarked(self):
        self.assertNotIn('required_auth', resolve(reverse('api_support_customer')).extra_kwargs)
        self.assertNotIn('required_auth', resolve(reverse('appointment_caldav_setup')).extra_kwargs)


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
