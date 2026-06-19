import json
from datetime import timezone as datetime_timezone
from unittest.mock import Mock, patch

import jwt
from django.conf import settings
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.test import Client as RequestClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.core.zendesk_sidebar import (
    _set_zendesk_frame_ancestors,
    _validate_zendesk_oauth_token,
    _validate_zendesk_signed_token,
    get_customer_sidebar_data,
)
from thunderbird_accounts.core.utils import get_absolute_url
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.models import Account, Domain, Email
from thunderbird_accounts.subscription.models import Plan, Subscription, Transaction


class ZendeskCustomerSidebarLookupTestCase(TestCase):
    def test_missing_email_returns_not_user_status(self):
        payload = get_customer_sidebar_data('missing@example.com', 'web')

        self.assertFalse(payload['found'])
        self.assertEqual(payload['status']['code'], 'not_user')
        self.assertEqual(payload['status']['label'], 'Not signed up')
        self.assertFalse(payload['verification']['verified'])
        self.assertIsNone(payload['profile'])
        self.assertIsNone(payload['subscription'])

    def test_allow_list_entry_without_user_returns_allow_list_status(self):
        allow_list_entry = AllowListEntry.objects.create(email='allowed@example.com', discount_id='dsc_123')

        payload = get_customer_sidebar_data('ALLOWED@example.com', 'api')

        self.assertTrue(payload['found'])
        self.assertEqual(payload['status']['code'], 'allow_list')
        self.assertEqual(payload['status']['label'], 'On allow list')
        self.assertTrue(payload['verification']['verified'])
        self.assertEqual(payload['allow_list']['email'], 'allowed@example.com')
        self.assertEqual(payload['allow_list']['discount_id'], 'dsc_123')
        self.assertEqual(
            payload['links']['allow_list_admin'],
            reverse('admin:authentication_allowlistentry_change', args=[allow_list_entry.pk]),
        )

    def test_unpaid_user_returns_user_unpaid_status(self):
        user = User.objects.create(
            username=f'unpaid@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='requester@example.com',
            recovery_email='recovery@example.com',
            display_name='Unpaid User',
        )
        account = Account.objects.create(name=user.username, user=user, quota=settings.ONE_GIGABYTE_IN_BYTES)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)

        payload = get_customer_sidebar_data('requester@example.com', 'web')

        self.assertTrue(payload['found'])
        self.assertEqual(payload['status']['code'], 'user_unpaid')
        self.assertEqual(payload['status']['label'], 'User created')
        self.assertFalse(payload['status']['payment_verification_pending'])
        self.assertEqual(payload['profile']['primary_email'], user.username)
        self.assertEqual(payload['profile']['recovery_email'], 'recovery@example.com')
        self.assertEqual(payload['profile']['display_name'], 'Unpaid User')
        self.assertEqual(payload['links']['user_admin'], reverse('admin:authentication_user_change', args=[user.pk]))

    def test_payment_verification_pending_is_flagged_on_unpaid_user(self):
        User.objects.create(
            username=f'pending@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='pending@example.com',
            recovery_email='pending@example.com',
            display_name='Pending User',
            is_awaiting_payment_verification=True,
        )

        payload = get_customer_sidebar_data('pending@example.com', 'api')

        self.assertEqual(payload['status']['code'], 'user_unpaid')
        self.assertTrue(payload['status']['payment_verification_pending'])
        self.assertTrue(payload['verification']['verified'])

    @patch('thunderbird_accounts.core.zendesk_sidebar.MailClient')
    @override_settings(PADDLE_VENDOR_SITE='https://vendors.paddle.com')
    def test_paid_user_aggregates_profile_subscription_quota_and_links(self, mock_mail_client_cls):
        mock_mail_client = Mock()
        mock_mail_client.get_account.return_value = {
            'quota': settings.ONE_GIGABYTE_IN_BYTES * 10,
            'usedQuota': 0,
            'description': 'Stalwart Display',
            'secrets': ['$app$Thunderbird$hashed-password'],
        }
        mock_mail_client_cls.return_value = mock_mail_client

        plan = Plan.objects.create(
            name='Thundermail Plus',
            mail_address_count=10,
            mail_domain_count=2,
            mail_storage_bytes=settings.ONE_GIGABYTE_IN_BYTES * 10,
            send_storage_bytes=settings.ONE_GIGABYTE_IN_BYTES,
        )
        user = User.objects.create(
            username=f'paid@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='requester@example.com',
            recovery_email='recovery@example.net',
            display_name='Paid User',
            plan=plan,
        )
        account = Account.objects.create(name=user.username, user=user, quota=settings.ONE_GIGABYTE_IN_BYTES * 10)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        Email.objects.create(address='alias@example.org', type=Email.EmailType.ALIAS, account=account)
        Email.objects.create(address='@custom.example', type=Email.EmailType.ALIAS, account=account)
        verified_at = timezone.datetime(2026, 5, 1, 9, 30, tzinfo=datetime_timezone.utc)
        last_verification_attempt = timezone.datetime(2026, 5, 2, 10, 45, tzinfo=datetime_timezone.utc)
        Domain.objects.create(
            name='custom.example',
            status=Domain.DomainStatus.VERIFIED,
            verified_at=verified_at,
            last_verification_attempt=last_verification_attempt,
            user=user,
        )
        Domain.objects.create(
            name='pending.example',
            status=Domain.DomainStatus.PENDING,
            last_verification_attempt=last_verification_attempt,
            user=user,
        )

        subscription = Subscription.objects.create(
            paddle_id='sub_123',
            paddle_customer_id='ctm_123',
            status=Subscription.StatusValues.ACTIVE,
            next_billed_at=timezone.datetime(2026, 6, 1, 12, 0, tzinfo=datetime_timezone.utc),
            user=user,
            discount_amount='25',
            discount_type=Subscription.DiscountTypes.PERCENTAGE,
        )
        Transaction.objects.create(
            paddle_id='txn_1',
            total='1200',
            tax='0',
            currency='USD',
            status=Transaction.StatusValues.PAID,
            transaction_origin=Transaction.OriginValues.WEB,
            subscription=subscription,
        )
        Transaction.objects.create(
            paddle_id='txn_2',
            total='1500',
            tax='0',
            currency='USD',
            status=Transaction.StatusValues.COMPLETED,
            transaction_origin=Transaction.OriginValues.SUBSCRIPTION_RECURRING,
            subscription=subscription,
        )
        Transaction.objects.create(
            paddle_id='txn_draft',
            total='9999',
            tax='0',
            currency='USD',
            status=Transaction.StatusValues.DRAFT,
            transaction_origin=Transaction.OriginValues.WEB,
            subscription=subscription,
        )

        payload = get_customer_sidebar_data('alias@example.org', 'api')

        self.assertEqual(payload['status']['code'], 'user_paid')
        self.assertEqual(payload['status']['label'], 'Paid')
        self.assertEqual(payload['profile']['primary_email'], user.username)
        self.assertEqual(payload['profile']['display_name'], 'Stalwart Display')
        self.assertEqual(payload['profile']['aliases'], ['alias@example.org'])
        self.assertEqual(payload['profile']['catch_alls'], ['@custom.example'])
        self.assertEqual(payload['profile']['custom_domain_counts'], {'verified': 1, 'pending': 1})
        self.assertEqual(
            payload['profile']['custom_domains'],
            [
                {
                    'name': 'custom.example',
                    'status': 'verified',
                    'verified_at': verified_at.isoformat(),
                    'last_verification_attempt': last_verification_attempt.isoformat(),
                },
                {
                    'name': 'pending.example',
                    'status': 'pending',
                    'verified_at': None,
                    'last_verification_attempt': last_verification_attempt.isoformat(),
                },
            ],
        )
        self.assertEqual(payload['profile']['app_password_set'], True)
        self.assertEqual(payload['quota']['used_bytes'], 0)
        self.assertEqual(payload['quota']['used_display'], '0 B')
        self.assertEqual(payload['quota']['limit_bytes'], settings.ONE_GIGABYTE_IN_BYTES * 10)
        self.assertEqual(payload['subscription']['status'], Subscription.StatusValues.ACTIVE)
        self.assertEqual(payload['subscription']['plan'], 'Thundermail Plus')
        self.assertEqual(payload['subscription']['discount'], {'amount': '25', 'type': 'percentage'})
        self.assertEqual(payload['subscription']['total_spend'], [{'currency': 'USD', 'amount': '27.00'}])
        self.assertEqual(
            payload['links']['subscription_admin'],
            reverse('admin:subscription_subscription_change', args=[subscription.pk]),
        )
        self.assertEqual(payload['links']['paddle_subscription'], 'https://vendors.paddle.com/subscriptions-v2/sub_123')
        self.assertEqual(payload['links']['paddle_customer'], 'https://vendors.paddle.com/customers-v2/ctm_123')
        mock_mail_client.get_account.assert_called_once_with(user.username)

    def test_empty_display_name_does_not_fall_back_to_email_address(self):
        user = User.objects.create(
            username=f'nodisplay@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='nodisplay@example.com',
            display_name='',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)

        payload = get_customer_sidebar_data('nodisplay@example.com', 'web')

        self.assertEqual(payload['profile']['display_name'], '')

    def test_email_display_name_is_hidden(self):
        user = User.objects.create(
            username=f'emaildisplay@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='emaildisplay@example.com',
            display_name='emaildisplay@example.com',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)

        payload = get_customer_sidebar_data('emaildisplay@example.com', 'web')

        self.assertEqual(payload['profile']['display_name'], '')

    def test_user_legal_acceptance_is_reported(self):
        user = User.objects.create(
            username=f'legal@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='legal@example.com',
            display_name='Legal User',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        tos = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )
        privacy = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.PRIVACY,
            version='3.0',
            is_current=True,
            content_path='privacy/v3.0',
        )
        tos_response = LegalDocumentResponse.objects.create(
            user=user,
            document=tos,
            action=LegalDocumentResponse.Action.ACCEPTED,
            source_context='sign-up',
        )
        LegalDocumentResponse.objects.create(
            user=user,
            document=privacy,
            action=LegalDocumentResponse.Action.DECLINED,
            source_context='dashboard',
        )

        payload = get_customer_sidebar_data('legal@example.com', 'web')

        self.assertEqual(
            payload['legal']['terms'],
            {
                'accepted': True,
                'accepted_at': tos_response.created_at.isoformat(),
                'version': '2.0',
            },
        )
        self.assertEqual(
            payload['legal']['privacy'],
            {
                'accepted': False,
                'accepted_at': None,
                'version': None,
            },
        )

    @patch('thunderbird_accounts.core.zendesk_sidebar.MailClient')
    def test_stalwart_email_display_name_falls_back_to_django_display_name(self, mock_mail_client_cls):
        mock_mail_client = Mock()
        mock_mail_client.get_account.return_value = {
            'quota': settings.ONE_GIGABYTE_IN_BYTES,
            'usedQuota': 0,
            'description': 'stalwartdisplay@example.com',
            'secrets': [],
        }
        mock_mail_client_cls.return_value = mock_mail_client

        user = User.objects.create(
            username=f'stalwartdisplay@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='stalwartdisplay@example.com',
            display_name='Django Display',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        Subscription.objects.create(status=Subscription.StatusValues.ACTIVE, user=user)

        payload = get_customer_sidebar_data('stalwartdisplay@example.com', 'web')

        self.assertEqual(payload['profile']['display_name'], 'Django Display')

    def test_ambiguous_user_matches_are_reported(self):
        User.objects.create(username=f'first@{settings.PRIMARY_EMAIL_DOMAIN}', email='shared@example.com')
        User.objects.create(username=f'second@{settings.PRIMARY_EMAIL_DOMAIN}', recovery_email='shared@example.com')

        payload = get_customer_sidebar_data('shared@example.com', 'api')

        self.assertFalse(payload['found'])
        self.assertEqual(payload['status']['code'], 'ambiguous')
        self.assertIn('multiple', payload['error'].lower())


class ZendeskCustomerSidebarViewTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.admin_user = User.objects.create_user(
            username='zendesk-admin@example.com',
            email='zendesk-admin@example.com',
            is_staff=True,
        )
        self.admin_user.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label__in=['authentication', 'mail', 'subscription'],
                codename__in=[
                    'view_account',
                    'view_allowlistentry',
                    'view_domain',
                    'view_email',
                    'view_subscription',
                    'view_transaction',
                    'view_user',
                ],
            )
        )
        self.client.force_login(self.admin_user)

    @override_settings(DEBUG=True)
    def test_content_route_requires_django_permissions(self):
        self.client.logout()

        response = self.client.get(reverse('zendesk_sidebar_content'), {'email': 'requester@example.com'})

        self.assertEqual(response.status_code, 401)
        self.assertContains(
            response,
            'Authorize Thundermail in the Zendesk app settings, then reload Zendesk.',
            status_code=401,
        )

    @override_settings(DEBUG=True)
    def test_content_route_rejects_staff_without_required_permissions(self):
        staff_user = User.objects.create_user(
            username='staff-content@example.com',
            email='staff-content@example.com',
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse('zendesk_sidebar_content'), {'email': 'requester@example.com'})

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Missing required Django permissions for the Zendesk sidebar.', status_code=403)

    @override_settings(DEBUG=True)
    def test_content_route_does_not_redirect_to_oidc_when_oidc_session_is_expired(self):
        session = self.client.session
        session['oidc_id_token_expiration'] = 1
        session['oidc_refresh_token'] = 'expired-refresh-token'
        session.save()

        response = self.client.get(reverse('zendesk_sidebar_content'))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response.headers)
        self.assertContains(response, 'No requester email is available.')

    @override_settings(DEBUG=True)
    def test_content_route_renders_missing_email_state(self):
        response = self.client.get(reverse('zendesk_sidebar_content'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
        self.assertIn("frame-ancestors 'self'", response.headers['Content-Security-Policy'])
        self.assertContains(response, 'No requester email is available.')
        self.assertContains(response, 'Not signed up')
        self.assertNotContains(response, 'zaf_sdk')

    @patch('thunderbird_accounts.core.zendesk_sidebar._validate_zendesk_signed_token')
    def test_sidebar_route_renders_zaf_shell(self, mock_validate_token):
        response = self.client.post(reverse('zendesk_sidebar'), {'token': 'signed-token'})

        self.assertEqual(response.status_code, 200)
        mock_validate_token.assert_called_once_with('signed-token')
        self.assertIn("frame-ancestors 'self'", response.headers['Content-Security-Policy'])
        self.assertContains(response, 'zaf_sdk.min.js')
        self.assertContains(response, 'ticket.requester.email')
        self.assertContains(response, 'app.registered')
        self.assertContains(response, 'app.activated')
        self.assertContains(response, get_absolute_url(reverse('zendesk_sidebar_content')))
        self.assertContains(response, 'zendeskClient.request')
        self.assertContains(response, 'secure: true')
        self.assertContains(
            response,
            "Authorization: 'Bearer {{setting.token}}'",
            html=False,
        )
        self.assertNotContains(response, 'oauthTokenPlaceholder')
        self.assertContains(response, '<iframe id="content-frame"', html=False)
        self.assertNotContains(response, 'zendesk_token')
        self.assertNotContains(response, 'contentForm.submit()')
        self.assertNotContains(response, 'Primary email')

    @patch('thunderbird_accounts.core.zendesk_sidebar._validate_zendesk_signed_token')
    def test_sidebar_route_uses_signed_token_without_django_session(self, mock_validate_token):
        self.client.logout()

        response = self.client.post(reverse('zendesk_sidebar'), {'token': 'signed-token'})

        self.assertEqual(response.status_code, 200)
        mock_validate_token.assert_called_once_with('signed-token')
        self.assertContains(response, 'zaf_sdk.min.js')

    @patch('thunderbird_accounts.core.zendesk_sidebar._validate_zendesk_oauth_token')
    def test_content_route_accepts_zendesk_oauth_staff_user_without_django_session(self, mock_validate_token):
        self.admin_user.oidc_id = 'keycloak-user-123'
        self.admin_user.save()
        mock_validate_token.return_value = {
            'sub': 'keycloak-user-123',
            'email': 'agent@example.com',
            'azp': 'zendesk-sidebar-stage',
        }
        User.objects.create(
            username=f'oauth@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='oauth-requester@example.com',
            display_name='Linked Requester',
        )
        self.client.logout()

        response = self.client.post(
            reverse('zendesk_sidebar_content'),
            json.dumps({
                'email': 'oauth-requester@example.com',
                'via': 'api',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer oauth-token',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Linked Requester')
        mock_validate_token.assert_called_once_with('oauth-token')

    @patch('thunderbird_accounts.core.zendesk_sidebar._validate_zendesk_oauth_token')
    def test_content_route_rejects_valid_oauth_user_without_local_account(self, mock_validate_token):
        mock_validate_token.return_value = {
            'sub': 'keycloak-missing-user',
            'email': 'agent@example.com',
            'azp': 'zendesk-sidebar-stage',
        }
        self.client.logout()

        response = self.client.post(
            reverse('zendesk_sidebar_content'),
            {'email': 'requester@example.com', 'via': 'api'},
            HTTP_AUTHORIZATION='Bearer oauth-token',
        )

        self.assertEqual(response.status_code, 401)
        self.assertContains(response, 'No Thundermail staff account is linked to agent@example.com.', status_code=401)

    @patch('thunderbird_accounts.core.zendesk_sidebar._validate_zendesk_oauth_token')
    def test_content_route_rejects_oauth_staff_without_sidebar_permissions(self, mock_validate_token):
        staff_user = User.objects.create_user(
            username='staff-oauth@example.com',
            email='staff-oauth@example.com',
            oidc_id='keycloak-staff-without-perms',
            is_staff=True,
        )
        mock_validate_token.return_value = {
            'sub': 'keycloak-staff-without-perms',
            'email': staff_user.email,
            'azp': 'zendesk-sidebar-stage',
        }
        self.client.logout()

        response = self.client.post(
            reverse('zendesk_sidebar_content'),
            {'email': 'requester@example.com', 'via': 'api'},
            HTTP_AUTHORIZATION='Bearer oauth-token',
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Missing required Django permissions for the Zendesk sidebar.', status_code=403)

    def test_content_route_rejects_post_without_oauth_token(self):
        self.client.logout()

        response = self.client.post(reverse('zendesk_sidebar_content'), {'email': 'requester@example.com'})

        self.assertEqual(response.status_code, 401)
        self.assertContains(
            response,
            'Authorize Thundermail in the Zendesk app settings, then reload Zendesk.',
            status_code=401,
        )

    @override_settings(
        ZENDESK_APP_PUBLIC_KEY='zendesk-public-key',
        ZENDESK_APP_AUDIENCE='https://example.zendesk.com/api/v2/apps/installations/123.json',
        ZENDESK_SUBDOMAIN='example',
    )
    @patch('thunderbird_accounts.core.zendesk_sidebar.jwt.decode')
    def test_signed_zendesk_token_validation_requires_audience(self, mock_decode):
        mock_decode.return_value = {
            'iss': 'example.zendesk.com',
            'context': {'product': 'support', 'location': 'ticket_sidebar'},
        }

        claims = _validate_zendesk_signed_token('signed-token')

        self.assertEqual(claims, mock_decode.return_value)
        mock_decode.assert_called_once_with(
            'signed-token',
            'zendesk-public-key',
            algorithms=['RS256'],
            audience='https://example.zendesk.com/api/v2/apps/installations/123.json',
            options={'require': ['exp', 'iat']},
        )

    @override_settings(
        ZENDESK_APP_PUBLIC_KEY='zendesk-public-key',
        ZENDESK_APP_AUDIENCE='https://example.zendesk.com/api/v2/apps/installations/123.json',
        ZENDESK_SUBDOMAIN='example',
    )
    @patch('thunderbird_accounts.core.zendesk_sidebar.jwt.decode')
    def test_signed_zendesk_token_validation_rejects_wrong_context(self, mock_decode):
        mock_decode.return_value = {
            'iss': 'example.zendesk.com',
            'context': {'product': 'support', 'location': 'user_sidebar'},
        }

        with self.assertRaises(ValueError):
            _validate_zendesk_signed_token('signed-token')

    @override_settings(
        ZENDESK_OAUTH_ISSUER='https://auth-stage.tb.pro/realms/tbpro',
        ZENDESK_OAUTH_AUDIENCE='zendesk-sidebar-stage',
        ZENDESK_OAUTH_CLIENT_ID='zendesk-sidebar-stage',
        ZENDESK_OAUTH_JWKS_ENDPOINT='https://auth-stage.tb.pro/realms/tbpro/protocol/openid-connect/certs',
    )
    @patch('thunderbird_accounts.core.zendesk_sidebar._get_zendesk_oauth_signing_key')
    @patch('thunderbird_accounts.core.zendesk_sidebar.jwt.decode')
    def test_oauth_token_validation_requires_keycloak_issuer_audience_and_client(
        self,
        mock_decode,
        mock_get_signing_key,
    ):
        mock_get_signing_key.return_value = 'keycloak-signing-key'
        mock_decode.return_value = {
            'sub': 'keycloak-user-123',
            'azp': 'zendesk-sidebar-stage',
        }

        claims = _validate_zendesk_oauth_token('oauth-token')

        self.assertEqual(claims, mock_decode.return_value)
        mock_get_signing_key.assert_called_once_with('oauth-token')
        mock_decode.assert_called_once_with(
            'oauth-token',
            'keycloak-signing-key',
            algorithms=['RS256'],
            audience='zendesk-sidebar-stage',
            issuer='https://auth-stage.tb.pro/realms/tbpro',
            options={'require': ['exp', 'iat', 'sub']},
        )

    @override_settings(
        ZENDESK_OAUTH_ISSUER='https://auth-stage.tb.pro/realms/tbpro',
        ZENDESK_OAUTH_AUDIENCE='zendesk-sidebar-stage',
        ZENDESK_OAUTH_CLIENT_ID='zendesk-sidebar-stage',
        ZENDESK_OAUTH_JWKS_ENDPOINT='https://auth-stage.tb.pro/realms/tbpro/protocol/openid-connect/certs',
    )
    @patch('thunderbird_accounts.core.zendesk_sidebar._get_zendesk_oauth_signing_key')
    @patch('thunderbird_accounts.core.zendesk_sidebar.jwt.decode')
    def test_oauth_token_validation_rejects_unexpected_client(self, mock_decode, mock_get_signing_key):
        mock_get_signing_key.return_value = 'keycloak-signing-key'
        mock_decode.return_value = {
            'sub': 'keycloak-user-123',
            'azp': 'other-client',
        }

        with self.assertRaises(jwt.InvalidTokenError):
            _validate_zendesk_oauth_token('oauth-token')

    @override_settings(
        CSRF_TRUSTED_ORIGINS=['https://autoconfig.example', 'https://support.example'],
        ZENDESK_SUBDOMAIN='example',
    )
    def test_frame_ancestors_csp_preserves_existing_restrictions(self):
        response = HttpResponse()
        response['Content-Security-Policy'] = "default-src 'none'; script-src 'self'"

        _set_zendesk_frame_ancestors(response)

        csp = response.headers['Content-Security-Policy']
        self.assertIn("default-src 'none'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'self'", csp)
        self.assertIn('https://autoconfig.example', csp)
        self.assertIn('https://support.example', csp)
        self.assertIn('https://example.zendesk.com', csp)

    @override_settings(ZENDESK_SUBDOMAIN='example')
    def test_zendesk_sidebar_middleware_adds_frame_ancestors_to_sidebar_prefix_responses(self):
        response = self.client.get('/zendesk/sidebar/content/')

        self.assertIn("frame-ancestors 'self'", response.headers['Content-Security-Policy'])
        self.assertIn('https://example.zendesk.com', response.headers['Content-Security-Policy'])
        self.assertNotIn('X-Frame-Options', response.headers)

    @override_settings(DEBUG=True)
    def test_content_route_renders_not_signed_up_state(self):
        response = self.client.get(
            reverse('zendesk_sidebar_content'),
            {'email': 'missing@example.com', 'via': 'web'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not signed up')
        self.assertContains(response, 'Not verified')

    @override_settings(DEBUG=True)
    def test_content_route_renders_compact_sidebar(self):
        plan = Plan.objects.create(
            name='Thundermail Starter',
            mail_address_count=3,
            mail_domain_count=1,
            mail_storage_bytes=settings.ONE_GIGABYTE_IN_BYTES,
            send_storage_bytes=settings.ONE_GIGABYTE_IN_BYTES,
        )
        user = User.objects.create(
            username=f'preview@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='preview@example.com',
            recovery_email='recovery@example.com',
            display_name='Preview User',
            plan=plan,
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        Email.objects.create(address='alias@example.org', type=Email.EmailType.ALIAS, account=account)

        response = self.client.get(
            reverse('zendesk_sidebar_content'),
            {'email': 'preview@example.com', 'via': 'api'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview User')
        self.assertContains(response, 'Verified')
        self.assertContains(response, user.username)
        self.assertContains(response, 'recovery@example.com')
        self.assertContains(response, 'Not set')
        self.assertContains(response, 'Thundermail Starter')
        self.assertContains(response, '<summary>1 alias</summary>', html=False)
        self.assertContains(response, '<summary>0 catch-alls</summary>', html=False)
        self.assertContains(response, '<summary>0 domains (0 verified, 0 pending)</summary>', html=False)
        self.assertContains(response, 'alias@example.org')
        self.assertContains(response, 'data-date=', html=False)

    @override_settings(DEBUG=True)
    def test_content_route_renders_legal_acceptance(self):
        user = User.objects.create(
            username=f'legal-render@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='legal-render@example.com',
            display_name='Legal Render User',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        tos = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )
        LegalDocumentResponse.objects.create(
            user=user,
            document=tos,
            action=LegalDocumentResponse.Action.ACCEPTED,
            source_context='sign-up',
        )

        response = self.client.get(
            reverse('zendesk_sidebar_content'),
            {'email': 'legal-render@example.com', 'via': 'api'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Terms accepted')
        self.assertContains(response, 'Privacy accepted')
        self.assertContains(response, 'Yes, version 2.0')
        self.assertContains(response, 'No')
        self.assertContains(response, 'data-date=', html=False)

    @override_settings(DEBUG=True)
    def test_content_route_renders_custom_domains_in_details(self):
        user = User.objects.create(
            username=f'domains@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='domains@example.com',
            display_name='Domain User',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        verified_at = timezone.datetime(2026, 5, 1, 9, 30, tzinfo=datetime_timezone.utc)
        Domain.objects.create(
            name='alpha.example',
            status=Domain.DomainStatus.VERIFIED,
            verified_at=verified_at,
            user=user,
        )
        Domain.objects.create(
            name='beta.example',
            status=Domain.DomainStatus.PENDING,
            user=user,
        )

        response = self.client.get(
            reverse('zendesk_sidebar_content'),
            {'email': 'domains@example.com', 'via': 'api'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<summary>2 domains (1 verified, 1 pending)</summary>', html=False)
        self.assertContains(response, 'alpha.example (verified)')
        self.assertContains(response, 'beta.example (pending)')
        self.assertContains(
            response,
            'href="https://mxtoolbox.com/emailhealth/alpha.example" target="_blank" rel="noopener noreferrer"',
            html=False,
        )
        self.assertContains(
            response,
            'href="https://mxtoolbox.com/emailhealth/beta.example" target="_blank" rel="noopener noreferrer"',
            html=False,
        )
        self.assertContains(response, 'title="Verified at: 2026-05-01T09:30:00+00:00"', html=False)
        self.assertContains(response, 'data-domain-tooltip-date="2026-05-01T09:30:00+00:00"', html=False)
        self.assertContains(response, 'title="Last verification attempt: never"', html=False)
        self.assertContains(response, 'data-domain-tooltip-date=""', html=False)

    @override_settings(DEBUG=True)
    def test_content_route_renders_single_custom_domain_in_details(self):
        user = User.objects.create(
            username=f'domain@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='domain@example.com',
            display_name='Domain User',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        verified_at = timezone.datetime(2026, 5, 1, 9, 30, tzinfo=datetime_timezone.utc)
        Domain.objects.create(
            name='single.example',
            status=Domain.DomainStatus.VERIFIED,
            verified_at=verified_at,
            user=user,
        )

        response = self.client.get(
            reverse('zendesk_sidebar_content'),
            {'email': 'domain@example.com', 'via': 'api'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<summary>1 domain (1 verified, 0 pending)</summary>', html=False)
        self.assertContains(response, 'single.example (verified)')
        self.assertContains(
            response,
            'href="https://mxtoolbox.com/emailhealth/single.example" target="_blank" rel="noopener noreferrer"',
            html=False,
        )
        self.assertContains(response, 'title="Verified at: 2026-05-01T09:30:00+00:00"', html=False)
