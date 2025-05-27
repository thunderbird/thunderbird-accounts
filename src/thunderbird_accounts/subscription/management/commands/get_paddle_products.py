"""
Create a new Client, with a Client Contact and optionally a Client Environment.
"""

import datetime
import enum

from django.core.management.base import BaseCommand
from thunderbird_accounts.subscription.decorators import inject_paddle
from thunderbird_accounts.subscription.models import Product

try:
    from paddle_billing import Client
except ImportError:
    Client = None


class Command(BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py get_paddle_products [--dry]

    """

    class ReturnCodes(enum.StrEnum):
        OK = 'OK'
        ERROR = 'ERROR'  # Generic error, shouldn't normally be set
        NOT_SETUP = 'NOT_SETUP'

    help = 'Retrieves and updates products defined in Paddle.'

    def add_arguments(self, parser):
        parser.add_argument('--dry', help="Don't update anything.", action='store_true')

    @inject_paddle
    def handle(self, paddle: Client, *args, **options):
        if not paddle:
            self.stdout.write(self.style.NOTICE('Paddle is not setup.'))
            return self.ReturnCodes.NOT_SETUP

        dry_run = options.get('dry', False)
        verbosity = options.get('verbosity', 1)

        products = paddle.products.list()

        retrieved = 0
        created = 0
        updated = 0
        ignored = 0

        occurred_at = datetime.datetime.now(datetime.UTC)

        # This may call additional pages on iteration
        for product in products:
            retrieved += 1
            print(product)
            if dry_run:
                continue

            paddle_id = product.id

            # Not really needed, but we don't have any locks setup so there's a slim chance we could run into update
            # timing shenanigans with webhooks.
            try:
                product = Product.objects.filter(paddle_id=paddle_id).filter(webhook_updated_at__gt=occurred_at).get()
                if product:
                    ignored += 1
                    continue
            except Product.DoesNotExist:
                pass

            name = product.name
            description = product.description
            product_type = product.type
            status = product.status

            # Okay now we can just do a big update.
            product, product_created = Product.objects.update_or_create(
                paddle_id=paddle_id,
                defaults={
                    'name': name,
                    'description': description,
                    'product_type': product_type,
                    'status': status,
                    'webhook_updated_at': occurred_at,
                },
            )

            if product_created:
                created += 1
            else:
                updated += 1

        if verbosity > 0:
            self.stdout.write(self.style.SUCCESS('Finished retrieving Paddle products:'))
            self.stdout.write(self.style.SUCCESS(f'* {retrieved} products retrieved from Paddle API.'))
            self.stdout.write(self.style.SUCCESS(f'* {created} products created.'))
            self.stdout.write(self.style.SUCCESS(f'* {updated} products updated.'))
            self.stdout.write(self.style.SUCCESS(f'* {ignored} products ignored due to data being older than db.'))

        return self.ReturnCodes.OK.value
