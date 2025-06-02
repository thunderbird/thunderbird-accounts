"""
Create a new Client Environment from a given Client UUID.
"""

import enum

from django.core.management.base import BaseCommand
from thunderbird_accounts.subscription import models


class Command(BaseCommand):
    """
    Used for e2e tests to bootstrap the required plan objects.

    This takes in paddle_product_id to make things easier for the test setup.

    Usage:

    .. code-block:: shell

        python manage.py create_plan_for_e2e_test name <paddle_product_id>

    """

    class ReturnCodes(enum.StrEnum):
        OK = 'OK'
        ERROR = 'ERROR'  # Generic error, shouldn't normally be set
        ALREADY_EXISTS = 'ALREADY_EXISTS'
        PRODUCT_DOES_NOT_EXIST = 'PRODUCT_DOES_NOT_EXIST'

    help = 'Creates a plan object'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Name of the plan')
        parser.add_argument('paddle_product_id', type=str, help='Paddle product id (starts with pro_)')

    def handle(self, *args, **options):
        name = options.get('name')
        paddle_product_id = options.get('paddle_product_id')
        verbosity = options.get('verbosity', 1)

        product = models.Product.objects.filter(paddle_id=paddle_product_id).first()

        if not product:
            if verbosity > 0:
                self.stdout.write(self.style.ERROR('Failed to create test plan.'))
            return self.ReturnCodes.PRODUCT_DOES_NOT_EXIST.value

        plan = models.Plan.objects.create(
            name=name,
            visible_on_subscription_page=True,
            product_id=product.uuid,
        )

        if verbosity > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully created test plan {plan.uuid}'))

        return self.ReturnCodes.OK.value
