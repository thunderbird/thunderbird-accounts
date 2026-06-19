from datetime import timezone as datetime_timezone
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.models import Account, Domain, Email
from thunderbird_accounts.subscription.models import Plan, Subscription, Transaction
from thunderbird_accounts.support.customer import get_customer_support_data, support_customer_api

SUPPORT_CUSTOMER_VIEW_PERMISSIONS = [
    'authentication.view_user',
    'authentication.view_allowlistentry',
    'mail.view_account',
    'mail.view_email',
    'mail.view_domain',
    'legal.view_legaldocument',
    'legal.view_legaldocumentresponse',
    'subscription.view_plan',
    'subscription.view_subscription',
    'subscription.view_transaction',
]


class SupportCustomerLookupTestCase(TestCase):
    def create_viewer(self, *permissions):
        viewer = User.objects.create(
            username=f'viewer-{User.objects.count()}@{settings.PRIMARY_EMAIL_DOMAIN}',
            is_staff=True,
        )
        query = Permission.objects.none()
        for permission in permissions:
            if isinstance(permission, str):
                app_label, codename = permission.split('.', 1)
            else:
                app_label, codename = permission
            query |= Permission.objects.filter(content_type__app_label=app_label, codename=codename)
        viewer.user_permissions.add(*query)
        return viewer

    def create_full_viewer(self):
        return self.create_viewer(*SUPPORT_CUSTOMER_VIEW_PERMISSIONS)

    def test_missing_email_returns_not_user_status(self):
        payload = get_customer_support_data('missing@example.com', self.create_full_viewer())

        self.assertFalse(payload['found'])
        self.assertIsNone(payload['error'])
        self.assertIsNone(payload['profile'])
        self.assertIsNone(payload['subscription'])

    @override_settings(PUBLIC_BASE_URL='https://accounts.example.test')
    def test_allow_list_entry_without_user_returns_allow_list_status(self):
        allow_list_entry = AllowListEntry.objects.create(email='allowed@example.com', discount_id='dsc_123')

        payload = get_customer_support_data('ALLOWED@example.com', self.create_full_viewer())

        self.assertTrue(payload['found'])
        self.assertIsNone(payload['profile'])
        self.assertIsNone(payload['subscription'])
        self.assertEqual(payload['allow_list']['email'], 'allowed@example.com')
        self.assertEqual(payload['allow_list']['discount_id'], 'dsc_123')
        self.assertEqual(
            payload['links']['allow_list_admin'],
            'https://accounts.example.test'
            + reverse('admin:authentication_allowlistentry_change', args=[allow_list_entry.pk]),
        )

    @override_settings(PUBLIC_BASE_URL='https://accounts.example.test')
    def test_unpaid_user_returns_user_unpaid_status(self):
        user = User.objects.create(
            username=f'unpaid@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='requester@example.com',
            recovery_email='recovery@example.com',
            display_name='Unpaid User',
        )
        account = Account.objects.create(name=user.username, user=user, quota=settings.ONE_GIGABYTE_IN_BYTES)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)

        payload = get_customer_support_data('requester@example.com', self.create_full_viewer())

        self.assertTrue(payload['found'])
        self.assertEqual(payload['profile']['primary_email'], user.username)
        self.assertEqual(payload['profile']['recovery_email'], 'recovery@example.com')
        self.assertEqual(payload['profile']['display_name'], 'Unpaid User')
        self.assertIsNone(payload['subscription'])
        self.assertEqual(
            payload['links']['user_admin'],
            'https://accounts.example.test' + reverse('admin:authentication_user_change', args=[user.pk]),
        )

    def test_payment_verification_pending_is_flagged_on_unpaid_user(self):
        User.objects.create(
            username=f'pending@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='pending@example.com',
            recovery_email='pending@example.com',
            display_name='Pending User',
            is_awaiting_payment_verification=True,
        )

        payload = get_customer_support_data('pending@example.com', self.create_full_viewer())

        self.assertIsNone(payload['subscription'])

    @patch('thunderbird_accounts.support.customer.MailClient')
    @override_settings(PADDLE_VENDOR_SITE='https://vendors.paddle.com', PUBLIC_BASE_URL='https://accounts.example.test')
    def test_paid_user_aggregates_profile_subscription_quota_and_links(self, mock_mail_client_cls):
        mock_mail_client = Mock()
        stalwart_quota = settings.ONE_GIGABYTE_IN_BYTES * 12
        mock_mail_client.get_account.return_value = {
            'quota': stalwart_quota,
            'usedQuota': 0,
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

        payload = get_customer_support_data('alias@example.org', self.create_full_viewer())

        self.assertEqual(payload['profile']['primary_email'], user.username)
        self.assertEqual(payload['profile']['display_name'], 'Paid User')
        self.assertEqual(payload['profile']['aliases'], ['alias@example.org'])
        self.assertEqual(payload['profile']['catch_alls'], ['@custom.example'])
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
        self.assertEqual(payload['quota']['limit_bytes'], stalwart_quota)
        self.assertEqual(payload['subscription']['status'], Subscription.StatusValues.ACTIVE)
        self.assertEqual(payload['subscription']['plan'], 'Thundermail Plus')
        self.assertFalse(payload['subscription']['pending_verification'])
        self.assertEqual(payload['subscription']['discount'], {'amount': '25', 'type': 'percentage'})
        self.assertEqual(payload['subscription']['total_spend'], [{'currency': 'USD', 'amount': '27.00'}])
        self.assertEqual(
            payload['links']['subscription_admin'],
            'https://accounts.example.test' + reverse('admin:subscription_subscription_change', args=[subscription.pk]),
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

        payload = get_customer_support_data('nodisplay@example.com', self.create_full_viewer())

        self.assertEqual(payload['profile']['display_name'], '')

    def test_email_display_name_is_hidden(self):
        user = User.objects.create(
            username=f'emaildisplay@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='emaildisplay@example.com',
            display_name='emaildisplay@example.com',
        )
        account = Account.objects.create(name=user.username, user=user)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)

        payload = get_customer_support_data('emaildisplay@example.com', self.create_full_viewer())

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

        payload = get_customer_support_data('legal@example.com', self.create_full_viewer())

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

    def test_ambiguous_user_matches_are_reported(self):
        User.objects.create(username=f'first@{settings.PRIMARY_EMAIL_DOMAIN}', email='shared@example.com')
        User.objects.create(username=f'second@{settings.PRIMARY_EMAIL_DOMAIN}', recovery_email='shared@example.com')

        payload = get_customer_support_data('shared@example.com', self.create_full_viewer())

        self.assertIn('multiple', payload['error'].lower())

    def test_staff_with_partial_support_permission_receives_empty_payload(self):
        viewer = self.create_viewer(('authentication', 'view_user'))

        payload = get_customer_support_data('missing@example.com', viewer)

        self.assertFalse(payload['found'])
        self.assertIsNone(payload['profile'])
        self.assertIsNone(payload['subscription'])
        self.assertEqual(payload['links'], {})

    def test_staff_without_support_permissions_receives_empty_payload_from_api(self):
        User.objects.create(
            username=f'noperms@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='noperms@example.com',
            display_name='No Permissions',
        )
        viewer = self.create_viewer()
        request = APIRequestFactory().post(
            '/api/v1/support/customer/',
            {'email': 'noperms@example.com', 'via': 'api'},
            format='json',
        )
        force_authenticate(request, user=viewer)

        response = support_customer_api(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['found'])
        self.assertIsNone(response.data['profile'])
        self.assertIsNone(response.data['subscription'])
        self.assertEqual(response.data['links'], {})

    def test_non_staff_viewer_receives_403_even_with_model_permissions(self):
        user = User.objects.create(
            username=f'nonstaff-target@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='nonstaff-target@example.com',
            display_name='Hidden User',
        )
        viewer = self.create_viewer(('authentication', 'view_user'))
        viewer.is_staff = False
        viewer.save()
        request = APIRequestFactory().post(
            '/api/v1/support/customer/',
            {'email': user.email, 'via': 'api'},
            format='json',
        )
        force_authenticate(request, user=viewer)

        response = support_customer_api(request)

        self.assertEqual(response.status_code, 403)

    def test_inactive_staff_viewer_receives_403(self):
        user = User.objects.create(
            username=f'inactive-target@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='inactive-target@example.com',
            display_name='Hidden User',
        )
        viewer = self.create_viewer(('authentication', 'view_user'))
        viewer.is_active = False
        viewer.save()
        request = APIRequestFactory().post(
            '/api/v1/support/customer/',
            {'email': user.email, 'via': 'api'},
            format='json',
        )
        force_authenticate(request, user=viewer)

        response = support_customer_api(request)

        self.assertEqual(response.status_code, 403)

    def test_limited_viewer_does_not_receive_unpermitted_sections(self):
        user = User.objects.create(
            username=f'limited@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='limited@example.com',
            recovery_email='limited-recovery@example.com',
            display_name='Limited User',
        )
        plan = Plan.objects.create(name='Limited Plan')
        user.plan = plan
        user.save()
        account = Account.objects.create(name=user.username, user=user, quota=settings.ONE_GIGABYTE_IN_BYTES)
        Email.objects.create(address=user.username, type=Email.EmailType.PRIMARY, account=account)
        Email.objects.create(address='limited-alias@example.org', type=Email.EmailType.ALIAS, account=account)
        Domain.objects.create(name='limited.example', status=Domain.DomainStatus.VERIFIED, user=user)
        subscription = Subscription.objects.create(status=Subscription.StatusValues.ACTIVE, user=user)
        Transaction.objects.create(
            paddle_id='txn_limited',
            total='1200',
            tax='0',
            currency='USD',
            status=Transaction.StatusValues.PAID,
            transaction_origin=Transaction.OriginValues.WEB,
            subscription=subscription,
        )
        document = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.TOS,
            version='2.0',
            is_current=True,
            content_path='tos/v2.0',
        )
        LegalDocumentResponse.objects.create(
            user=user,
            document=document,
            action=LegalDocumentResponse.Action.ACCEPTED,
            source_context='sign-up',
        )
        viewer = self.create_viewer(('authentication', 'view_user'))

        payload = get_customer_support_data('limited@example.com', viewer)

        self.assertFalse(payload['found'])
        self.assertIsNone(payload['profile'])
        self.assertIsNone(payload['quota'])
        self.assertIsNone(payload['subscription'])
        self.assertIsNone(payload['legal'])
        self.assertEqual(payload['links'], {})

    def test_subscription_requires_full_profile_and_subscription_permissions(self):
        plan = Plan.objects.create(name='Thundermail Plus')
        user = User.objects.create(
            username=f'plan@{settings.PRIMARY_EMAIL_DOMAIN}',
            email='plan@example.com',
            plan=plan,
        )
        Subscription.objects.create(status=Subscription.StatusValues.ACTIVE, user=user)
        viewer = self.create_viewer(
            ('authentication', 'view_user'),
            ('mail', 'view_account'),
            ('mail', 'view_email'),
            ('subscription', 'view_subscription'),
            ('subscription', 'view_plan'),
        )

        payload = get_customer_support_data('plan@example.com', viewer)

        self.assertIsNone(payload['subscription'])

        viewer = self.create_viewer(
            ('authentication', 'view_user'),
            ('mail', 'view_account'),
            ('mail', 'view_email'),
            ('subscription', 'view_plan'),
            ('subscription', 'view_subscription'),
            ('subscription', 'view_transaction'),
        )
        payload = get_customer_support_data('plan@example.com', viewer)

        self.assertEqual(payload['subscription']['plan'], 'Thundermail Plus')
