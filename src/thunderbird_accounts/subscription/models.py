from django.db import models
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.utils.models import BaseModel


class PaddleId(models.CharField):
    """Holds a paddle id with some sensible defaults, but is otherwise just a CharField"""

    def __init__(self, *args, db_collation=None, **kwargs):
        kwargs = {'max_length': 256, 'db_index': True, 'null': True, 'default': None, **kwargs}
        super().__init__(*args, **kwargs)


class Price(BaseModel):
    """Paddle price object. A product can have multiple of these."""

    class TypeValues(models.TextChoices):
        # Paddle values
        STANDARD = 'standard', _('Standard')
        CUSTOM = 'custom', _('Custom')

    class IntervalValues(models.TextChoices):
        # Paddle values
        DAY = 'day', _('Day')
        WEEK = 'week', _('Week')
        MONTH = 'month', _('Month')
        YEAR = 'year', _('Year')

    paddle_id = PaddleId()
    paddle_product_id = PaddleId()
    name = models.CharField()
    amount = models.CharField(help_text=_('Amount in lowest denomination for currency. e.g. 10 USD = 1000 (cents).'))
    currency = models.CharField(help_text=_('Three letter ISO 4217 currency code.'))
    price_type = models.CharField(choices=TypeValues, help_text=_('Is this a one-off price?'))
    billing_cycle_frequency = models.CharField(help_text=_('Amount of time in a billing cycle.'))
    billing_cycle_interval = models.CharField(
        choices=IntervalValues, help_text=_('The unit of time in a billing cycle.')
    )

    def __str__(self):
        return f'Price [{self.uuid}] {self.name} - {self.paddle_id}'


class Plan(BaseModel):
    """A paddle product
    This will correspond with permissions/plans

    For now a plan has access to all clients
    """

    paddle_product_id = PaddleId()
    name = models.CharField(max_length=256)

    # Plan parameters
    mail_address_count = models.IntegerField(null=True, help_text=_('Amount of mail addresses a user can create.'))
    mail_domain_count = models.IntegerField(null=True, help_text=_('Amount of custom domains a user can have.'))
    mail_storage_gb = models.IntegerField(
        null=True, help_text=_('Amount of mail storage a user has access to (in GB).')
    )
    send_storage_gb = models.IntegerField(
        null=True, help_text=_('Amount of send storage a user has access to (in GB).')
    )

    def __str__(self):
        return f'Plan [{self.uuid}] {self.name} - {self.paddle_product_id}'


class SubscriptionItem(BaseModel):
    """An item from a subscription, a subscription should really only have one of these unless
    we add additional purchasable/subscribable items like addons."""

    quantity = models.IntegerField(default=0)
    paddle_price_id = PaddleId()
    paddle_product_id = PaddleId()
    paddle_subscription_id = PaddleId()

    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE)
    price = models.ForeignKey('Price', on_delete=models.CASCADE)

    def __str__(self):
        return f'Subscription Item [{self.uuid}] {self.subscription_id} - {self.paddle_product_id}'


class Subscription(BaseModel):
    """A paddle subscription object"""

    class StatusValues(models.TextChoices):
        # Empty value, non-paddle value
        NONE = '', _('None')

        # Paddle values
        ACTIVE = 'active', _('Active')
        CANCELED = 'canceled', _('Canceled')
        PAST_DUE = 'past_due', _('Past Due')
        PAUSED = 'paused', _('Paused')
        TRIALING = 'trialing', _('Trialing')

    class OriginValues(models.TextChoices):
        """Values from https://developer.paddle.com/webhooks/transactions/transaction-created -> origin"""

        API = 'api', _('Api')
        SUBSCRIPTION_CHARGE = (
            'subscription_charge',
            _('Subscription: Charge'),
        )
        SUBSCRIPTION_PAYMENT_METHOD_CHANGE = (
            'subscription_payment_method_change',
            _('Subscription: Payment method change'),
        )
        SUBSCRIPTION_RECURRING = 'subscription_recurring', _('Subscription: Recurring')
        SUBSCRIPTION_UPDATE = 'subscription_update', _('Subscription: Update')
        WEB = 'web', _('Web')

    paddle_id = PaddleId(help_text=_('The subscription paddle id.'))
    paddle_customer_id = PaddleId(help_text=_('The customer paddle id.'))
    status = models.CharField(
        max_length=256,
        choices=StatusValues,
        default=StatusValues.NONE,
        null=True,
        help_text=_('The current subscription status.'),
    )

    next_billed_at = models.DateTimeField(
        null=True, help_text=_('date when the subscription is next schedule to be billed.')
    )

    current_billing_period_starts_at = models.DateTimeField(
        null=True, help_text=_('date when the billing period starts.')
    )
    current_billing_period_ends_at = models.DateTimeField(null=True, help_text=_('date when the billing period ends.'))

    transaction_origin = models.CharField(
        choices=OriginValues, null=True, help_text=_('where the transaction first start from.')
    )

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'Subscription [{self.uuid}] {self.paddle_id} - {self.user.display_name}'

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['status']),
        ]
