from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command

from thunderbird_accounts.subscription.models import Product, Price


class GetPaddleProductTest(TestCase):
    def test_created_success(self):
        class ProductObj:
            id = 'pro_abc123'
            name = 'Product A'
            description = 'Hello World!'
            type = 'standard'
            status = 'active'

        with patch(
            'thunderbird_accounts.subscription.management.commands.get_paddle_products.Command.retrieve_paddle_data'
        ) as mock_retrieve_paddle_data:
            mock_retrieve_paddle_data.return_value = [ProductObj()]

            self.assertEqual(Product.objects.count(), 0)

            args = []
            opts = {}
            call_command('get_paddle_products', *args, **opts)

            self.assertEqual(Product.objects.count(), 1)

    def test_updated_success(self):
        class ProductObj:
            id = 'pro_abc123'
            name = 'Product A'
            description = 'Hello World!'
            type = 'standard'
            status = 'active'

        with patch(
            'thunderbird_accounts.subscription.management.commands.get_paddle_products.Command.retrieve_paddle_data'
        ) as mock_retrieve_paddle_data:
            product = Product.objects.create(
                name='Product A', product_type='standard', status='active', paddle_id='pro_abc123'
            )

            self.assertIsNotNone(product)
            self.assertIsNone(product.description)
            self.assertEqual(Product.objects.count(), 1)

            mock_retrieve_paddle_data.return_value = [ProductObj()]

            args = []
            opts = {}
            call_command('get_paddle_products', *args, **opts)

            self.assertEqual(Product.objects.count(), 1)

            product.refresh_from_db()

            self.assertIsNotNone(product.description)


class GetPaddlePriceTest(TestCase):
    def test_created_success(self):
        class UnitPriceObj:
            amount = '1000'
            currency_code = 'CAD'

        class BillingCycleObj:
            frequency = '1'
            interval = '1'

        class PriceObj:
            id = 'pri_abc123'
            name = 'Price A'
            unit_price = None
            billing_cycle = None
            type = 'standard'
            product_id = 'pro_abc123'

            def __init__(self):
                self.unit_price = UnitPriceObj()
                self.billing_cycle = BillingCycleObj()

        with patch(
            'thunderbird_accounts.subscription.management.commands.get_paddle_prices.Command.retrieve_paddle_data'
        ) as mock_retrieve_paddle_data:
            product = Product.objects.create(
                name='Product A', product_type='standard', status='active', paddle_id='pro_abc123'
            )

            mock_retrieve_paddle_data.return_value = [PriceObj()]

            self.assertEqual(Product.objects.count(), 1)
            self.assertEqual(Price.objects.count(), 0)

            args = []
            opts = {}
            call_command('get_paddle_prices', *args, **opts)

            self.assertEqual(Product.objects.count(), 1)
            self.assertEqual(Price.objects.count(), 1)

            price = Price.objects.first()
            self.assertIsNotNone(price)
            self.assertIsNotNone(price.product)
            self.assertEqual(price.product.uuid, product.uuid)

    def test_updated_success(self):
        class UnitPriceObj:
            amount = '1000'
            currency_code = 'CAD'

        class BillingCycleObj:
            frequency = '1'
            interval = '7'

        class PriceObj:
            id = 'pri_abc123'
            name = 'Price A'
            unit_price = None
            billing_cycle = None
            type = 'standard'
            product_id = 'pro_abc123'

            def __init__(self):
                self.unit_price = UnitPriceObj()
                self.billing_cycle = BillingCycleObj()

        with patch(
            'thunderbird_accounts.subscription.management.commands.get_paddle_prices.Command.retrieve_paddle_data'
        ) as mock_retrieve_paddle_data:
            product = Product.objects.create(
                name='Product A', product_type='standard', status='active', paddle_id='pro_abc123'
            )
            price = Price.objects.create(
                name='Price A',
                currency='CAD',
                price_type='standard',
                billing_cycle_frequency=1,
                billing_cycle_interval=1,
                paddle_product_id='pro_abc123',
                paddle_id='pri_abc123',
            )

            mock_retrieve_paddle_data.return_value = [PriceObj()]

            self.assertEqual(Product.objects.count(), 1)
            self.assertEqual(Price.objects.count(), 1)

            args = []
            opts = {}
            call_command('get_paddle_prices', *args, **opts)

            self.assertEqual(Product.objects.count(), 1)
            self.assertEqual(Price.objects.count(), 1)

            price.refresh_from_db()

            self.assertIsNotNone(price)
            self.assertIsNotNone(price.product)
            self.assertEqual(price.product.uuid, product.uuid)
            self.assertEqual(price.billing_cycle_interval, '7')
