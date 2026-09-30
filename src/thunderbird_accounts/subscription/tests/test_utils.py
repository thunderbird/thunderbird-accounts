from unittest.mock import patch
from thunderbird_accounts.subscription.utils import activate_subscription_features
import datetime
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.subscription.models import Plan, Product, Subscription, Transaction, SubscriptionItem, Price
from django.conf import settings
from thunderbird_accounts.authentication.models import User
from django.test import TestCase


class TestActivationSubscriptionFeatures(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            paddle_id='prod_1234',
            name='Test Pro',
            product_type=Product.TypeValues.STANDARD,
            status=Product.StatusValues.ACTIVE,
        )

        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        self.plan = Plan.objects.create(
            name='Test Plan',
            mail_address_count=10,
            mail_domain_count=10,
            mail_storage_bytes=10_000_000,
            send_storage_bytes=10_000_000,
        )

    def _create_subscription(
        self, status: Subscription.StatusValues = Subscription.StatusValues.ACTIVE, user: User | None = None
    ):
        sub = Subscription.objects.create(
            paddle_id='sub_1234',
            paddle_customer_id='cus_1234',
            status=status,
            user=user,
            next_billed_at=(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365)),  # 1 year from now!
        )
        # Not as fleshed out, don't test this!
        _trans = Transaction.objects.create(
            paddle_id='trx_1234',
            paddle_invoice_id='inv_1234',
            paddle_subscription_id=sub.paddle_id,
            status=Transaction.StatusValues.COMPLETED,
        )
        price = Price.objects.create(
            paddle_id='prc_1234',
            paddle_product_id=self.product.paddle_id,
            name='Standard Pro',
            amount='1000',
            currency='CAD',
            price_type=Price.TypeValues.STANDARD,
            billing_cycle_frequency='annual',
            billing_cycle_interval='year',
            product=self.product,
        )

        sub_item = SubscriptionItem.objects.create(
            quantity=1,
            paddle_price_id=price.paddle_id,
            paddle_product_id=self.product.paddle_id,
            paddle_subscription_id=sub.paddle_id,
            subscription=sub,
            price=price,
            product=self.product,
        )

        # Contains a link to everything
        return sub_item

    def test_success(self):
        """Test a fresh user without a stalwart account goes through our create_stalwart_account task"""
        _active_sub_item = self._create_subscription(user=self.user)

        with (
            patch('thunderbird_accounts.mail.tasks.update_quota_on_stalwart_account.delay') as update_quota_mock,
            patch('thunderbird_accounts.mail.tasks.create_stalwart_account.delay') as create_stalwart_account_mock,
            patch('thunderbird_accounts.subscription.utils.grant_mail_access_role.delay') as grant_role_mock,
        ):
            activate_subscription_features(user=self.user, plan=self.plan)

            update_quota_mock.assert_not_called()
            create_stalwart_account_mock.assert_called_once_with(
                oidc_id=self.user.oidc_id,
                username=self.user.username,
                email=self.user.username,
                full_name=None,
                app_password=None,
                quota=self.plan.mail_storage_bytes,
            )
            # The mailbox does not exist yet; only the provisioning task may grant the gate role.
            grant_role_mock.assert_not_called()

    def test_existing_stalwart_account_updates_quota_and_regrants_mail_access(self):
        _active_sub_item = self._create_subscription(user=self.user)
        Account.objects.create(name=self.user.username, user=self.user, stalwart_id='42', quota=1)

        with (
            patch('thunderbird_accounts.mail.tasks.update_quota_on_stalwart_account.delay') as update_quota_mock,
            patch('thunderbird_accounts.mail.tasks.create_stalwart_account.delay') as create_stalwart_account_mock,
            patch('thunderbird_accounts.subscription.utils.grant_mail_access_role.delay') as grant_role_mock,
        ):
            activate_subscription_features(user=self.user, plan=self.plan)

            create_stalwart_account_mock.assert_not_called()
            update_quota_mock.assert_called_with(username=self.user.username, quota=self.plan.mail_storage_bytes)
            grant_role_mock.assert_called_once_with(oidc_id=self.user.oidc_id)
