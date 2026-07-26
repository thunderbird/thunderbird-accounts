from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import Client as RequestClient, TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.core.tests.utils import oidc_force_login


class BulkImportAllowListTestCase(TestCase):
    _DISCOUNT_ID_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'

    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(
            username='admin@example.com',
            email='admin@example.com',
            oidc_id='admin-oidc-id',
            is_staff=True,
        )
        permission = Permission.objects.get(codename='add_allowlistentry')
        self.user.user_permissions.add(permission)
        oidc_force_login(self.client, self.user)

    def _make_discount_id(self):
        return f'dsc_{get_random_string(26, allowed_chars=self._DISCOUNT_ID_CHARS)}'

    def test_bulk_import_sets_row_discount_ids_for_new_entries(self):
        discount_id = self._make_discount_id()
        discount_id_2 = self._make_discount_id()

        response = self.client.post(
            reverse('allow_list_entry_import_submit'),
            {
                'bulk-entry': f'hello@example.com,{discount_id}\nhello2@example.com,{discount_id_2}',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AllowListEntry.objects.count(), 2)
        self.assertEqual(
            AllowListEntry.objects.get(email='hello@example.com').discount_id,
            discount_id,
        )
        self.assertEqual(
            AllowListEntry.objects.get(email='hello2@example.com').discount_id,
            discount_id_2,
        )

    def test_bulk_import_allows_rows_without_discount_ids(self):
        response = self.client.post(
            reverse('allow_list_entry_import_submit'),
            {
                'bulk-entry': 'hello@example.com\nhello2@example.com,',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AllowListEntry.objects.count(), 2)
        self.assertIsNone(AllowListEntry.objects.get(email='hello@example.com').discount_id)
        self.assertIsNone(AllowListEntry.objects.get(email='hello2@example.com').discount_id)

    def test_bulk_import_rejects_discount_ids_without_dsc_prefix(self):
        response = self.client.post(
            reverse('allow_list_entry_import_submit'),
            {
                'bulk-entry': 'hello@example.com,coupon_123',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AllowListEntry.objects.count(), 0)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(
            any(
                message.startswith('coupon_123 is not a valid discount id. Use the full Paddle id')
                for message in messages
            )
        )

    def test_bulk_import_rejects_short_dsc_discount_ids(self):
        response = self.client.post(
            reverse('allow_list_entry_import_submit'),
            {
                'bulk-entry': 'hello@example.com,dsc_123',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AllowListEntry.objects.count(), 0)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(
            any(
                message.startswith('dsc_123 is not a valid discount id. Use the full Paddle id')
                for message in messages
            )
        )
