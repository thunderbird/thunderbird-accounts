from django.db import models
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.utils.models import BaseModel


class PaddleId(models.CharField):
    """Holds a paddle id with some sensible defaults, but is otherwise just a CharField"""

    def __init__(self, *args, db_collation=None, **kwargs):
        kwargs = {'max_length': 256, 'db_index': True, 'null': True, 'default': None, **kwargs}
        super().__init__(*args, **kwargs)


class Product(BaseModel):
    class TypeValues(models.TextChoices):
        # Paddle values
        STANDARD = 'standard', _('Standard')
        CUSTOM = 'custom', _('Custom')

    class StatusValues(models.TextChoices):
        # Paddle values
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')

    paddle_id = PaddleId()
    name = models.CharField()
    description = models.TextField(null=True)
    product_type = models.CharField(
        choices=TypeValues, help_text=_('Is this a catalog product (standard) or a custom product?')
    )
    status = models.CharField(choices=StatusValues, help_text=_('Is this product active or archived (cannot be used.)'))
    webhook_updated_at = models.DateTimeField(
        null=True, help_text=_('date when this model was last updated by a paddle webhook.')
    )

    def __str__(self):
        return f'Product [{self.uuid}] {self.name} - {self.paddle_id} - ({self.status})'

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['name']),
            models.Index(fields=['product_type']),
            models.Index(fields=['status']),
            models.Index(fields=['webhook_updated_at']),
        ]


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

    class StatusValues(models.TextChoices):
        # Paddle values
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')

    paddle_id = PaddleId()
    paddle_product_id = PaddleId()
    name = models.CharField()
    amount = models.CharField(help_text=_('Amount in lowest denomination for currency. e.g. 10 USD = 1000 (cents).'))
    currency = models.CharField(help_text=_('Three letter ISO 4217 currency code.'))
    price_type = models.CharField(choices=TypeValues, help_text=_('Is this a one-off price?'))
    status = models.CharField(
        choices=StatusValues,
        default=StatusValues.ACTIVE,
        help_text=_('Is this price active or archived (cannot be used.)'),
    )
    billing_cycle_frequency = models.CharField(help_text=_('Amount of time in a billing cycle.'))
    billing_cycle_interval = models.CharField(
        choices=IntervalValues, help_text=_('The unit of time in a billing cycle.')
    )
    webhook_updated_at = models.DateTimeField(
        null=True, help_text=_('date when this model was last updated by a paddle webhook.')
    )

    product = models.ForeignKey('Product', null=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'Price [{self.uuid}] {self.name} - {self.paddle_id}'

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['currency']),
            models.Index(fields=['billing_cycle_frequency']),
            models.Index(fields=['billing_cycle_interval']),
            models.Index(fields=['webhook_updated_at']),
        ]


class Plan(BaseModel):
    """A paddle product
    This will correspond with permissions/plans

    For now a plan has access to all clients
    """

    name = models.CharField(max_length=256)
    visible_on_subscription_page = models.BooleanField(
        default=True, help_text=_('Is this plan visible on the subscription page?')
    )

    # Plan parameters
    mail_address_count = models.IntegerField(null=True, help_text=_('Amount of mail addresses a user can create.'))
    mail_domain_count = models.IntegerField(null=True, help_text=_('Amount of custom domains a user can have.'))
    mail_storage_gb = models.IntegerField(
        null=True, help_text=_('Amount of mail storage a user has access to (in GB).')
    )
    send_storage_gb = models.IntegerField(
        null=True, help_text=_('Amount of send storage a user has access to (in GB).')
    )

    product = models.ForeignKey('Product', null=True, on_delete=models.CASCADE)

    def __str__(self):
        if self.product:
            return f'Plan [{self.uuid}] {self.name} - {self.product.name}'
        return f'Plan [{self.uuid}] {self.name} - <Unassociated>'

    def save(self, **kwargs):
        """Override save to quickly check if the mail_storage_gb field has changed,
        if it has then ship off a task off to update each associated mail account.
        FIXME: This probably could be in a util function, I'm just worried we might not catch all updates."""
        from thunderbird_accounts.subscription import tasks

        previous_mail_storage_gb = None
        new_mail_storage_gb = None

        # Make sure we don't crash if this is during a create
        try:
            old_plan = Plan.objects.get(pk=self.uuid)
            previous_mail_storage_gb = old_plan.mail_storage_gb
            new_mail_storage_gb = self.mail_storage_gb
        except Plan.DoesNotExist:
            pass

        super().save(**kwargs)

        # Only ship the task out if the field has changed
        if previous_mail_storage_gb and new_mail_storage_gb and previous_mail_storage_gb != new_mail_storage_gb:
            tasks.update_thundermail_quota.delay(self.uuid, new_mail_storage_gb)


class SubscriptionItem(BaseModel):
    """An item from a subscription, a subscription should really only have one of these unless
    we add additional purchasable/subscribable items like addons."""

    quantity = models.IntegerField(default=0)
    paddle_price_id = PaddleId()
    paddle_product_id = PaddleId()
    paddle_subscription_id = PaddleId()

    # Subscription items MUST be related to a subscription object, but they can exclude price.
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE)
    price = models.ForeignKey('Price', null=True, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', null=True, on_delete=models.CASCADE)

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

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    webhook_updated_at = models.DateTimeField(
        null=True, help_text=_('date when this model was last updated by a paddle webhook.')
    )

    def __str__(self):
        return f'Subscription [{self.uuid}] {self.paddle_id} - {self.user.display_name}'

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['status']),
            models.Index(fields=['next_billed_at']),
            models.Index(fields=['current_billing_period_starts_at', 'current_billing_period_ends_at']),
            models.Index(fields=['webhook_updated_at']),
        ]


class Transaction(BaseModel):
    class StatusValues(models.TextChoices):
        # Empty value, non-paddle value
        NONE = '', _('None')

        # Paddle values
        DRAFT = 'draft', _('Draft')
        READY = 'ready', _('Ready')
        BILLED = 'billed', _('Billed')
        PAID = 'paid', _('Paid')
        COMPLETED = 'completed', _('Completed')
        CANCELED = 'canceled', _('Canceled')
        PAST_DUE = 'past_due', _('Past Due')

    class OriginValues(models.TextChoices):
        """Values from https://developer.paddle.com/webhooks/transactions/transaction-created -> origin"""

        NONE = '', _('None')

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

    paddle_id = PaddleId(help_text=_('The transaction paddle id.'))
    paddle_invoice_id = PaddleId(help_text=_('The invoice paddle id,'), null=True)
    paddle_subscription_id = PaddleId(help_text=_('The subscription paddle id.'), null=True)

    invoice_number = models.CharField(null=True, help_text=_('Invoice number for this transaction.'))

    total = models.CharField(max_length=256, null=False, help_text=_('Total after discount and tax.'))
    tax = models.CharField(max_length=256, null=False, help_text=_('Total tax on the subtotal.'))
    currency = models.CharField(max_length=256, null=False, help_text=_('Three letter ISO 4217 currency code.'))

    status = models.CharField(
        max_length=256,
        choices=StatusValues,
        default=StatusValues.NONE,
        null=False,
        help_text=_('The current subscription status.'),
    )

    transaction_origin = models.CharField(
        choices=OriginValues,
        null=False,
        default=OriginValues.NONE,
        help_text=_('where the transaction first start from.'),
    )

    billed_at = models.DateTimeField(
        null=True, help_text=_('date when the subscription is next schedule to be billed.')
    )
    revised_at = models.DateTimeField(
        null=True, help_text=_('date when the subscription is next schedule to be billed.')
    )
    webhook_updated_at = models.DateTimeField(
        null=True, help_text=_('date when this model was last updated by a paddle webhook.')
    )

    subscription = models.ForeignKey(Subscription, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'Transaction [{self.uuid}] {self.paddle_id} - ({self.status})'

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['invoice_number']),
            models.Index(fields=['transaction_origin']),
            models.Index(fields=['currency']),
            models.Index(fields=['status']),
            models.Index(fields=['billed_at']),
            models.Index(fields=['revised_at']),
            models.Index(fields=['webhook_updated_at']),
        ]
