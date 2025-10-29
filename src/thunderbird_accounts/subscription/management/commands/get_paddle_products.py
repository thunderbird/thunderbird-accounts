"""
Retrieves and updates products defined in Paddle.
"""

from django.core.management.base import BaseCommand
from paddle_billing.Entities.Shared import Status
from paddle_billing.Resources.Products.Operations import ListProducts

from thunderbird_accounts.subscription.management.commands import PaddleCommand
from thunderbird_accounts.subscription.models import Product

try:
    from paddle_billing import Client
except ImportError:
    Client = None


class Command(PaddleCommand, BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py get_paddle_products [--dry]

    """

    help = 'Retrieves and updates products defined in Paddle.'

    def retrieve_paddle_data(self, paddle: Client):
        """Return a paddle object's .list() return value."""
        return paddle.products.list(ListProducts(statuses=[Status.Active, Status.Archived]))

    def transform_paddle_data(self, paddle_obj):
        """Return a dict that will be passed in an update_or_create's default parameter.
        paddle_obj is an instance of a Paddle API object."""
        return {
            'paddle_id': paddle_obj.id,
            'name': paddle_obj.name,
            'description': paddle_obj.description,
            'product_type': paddle_obj.type,
            'status': paddle_obj.status,
        }

    def get_model(self):
        """Return the model that will be affected by this operation.
        Not an instance, just the class."""
        return Product
