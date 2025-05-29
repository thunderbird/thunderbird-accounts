"""
Retrieves and updates prices defined in Paddle.
"""

from django.core.management.base import BaseCommand
from thunderbird_accounts.subscription.management.commands import PaddleCommand
from thunderbird_accounts.subscription.models import Price, Product

try:
    from paddle_billing import Client
except ImportError:
    Client = None


class Command(PaddleCommand, BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py get_paddle_prices [--dry]

    """

    help = 'Retrieves and updates prices defined in Paddle.'

    def retrieve_paddle_data(self, paddle: Client):
        """Return a paddle object's .list() return value."""
        return paddle.prices.list()

    def transform_paddle_data(self, paddle_obj):
        """Return a dict that will be passed in an update_or_create's default parameter.
        paddle_obj is an instance of a Paddle API object."""
        unit_price = paddle_obj.unit_price
        billing_cycle = paddle_obj.billing_cycle
        product = None
        try:
            product = Product.objects.filter(paddle_id=paddle_obj.product_id).get()
        except Product.DoesNotExist:
            pass

        return {
            'paddle_product_id': paddle_obj.product_id,
            'name': paddle_obj.name,
            'amount': unit_price.amount,
            'currency': str(unit_price.currency_code),
            'price_type': str(paddle_obj.type),
            'billing_cycle_frequency': billing_cycle.frequency,
            'billing_cycle_interval': str(billing_cycle.interval),
            'product_id': product.uuid,
        }

    def get_model(self):
        """Return the model that will be affected by this operation.
        Not an instance, just the class."""
        return Price
