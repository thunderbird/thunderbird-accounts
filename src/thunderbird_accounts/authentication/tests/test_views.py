from django.contrib.auth.models import Permission
from django.test import Client as RequestClient, TestCase
from django.urls import reverse

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.core.tests.utils import oidc_force_login


class BulkImportAllowListTestCase(TestCase):
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

    def test_bulk_import_sets_discount_id_for_new_entries(self):
        response = self.client.post(
            reverse('allow_list_entry_import_submit'),
            {
                'bulk-entry': 'hello@example.com\nhello2@example.com',
                'discount-id': 'dsc_123',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AllowListEntry.objects.count(), 2)
        self.assertEqual(AllowListEntry.objects.get(email='hello@example.com').discount_id, 'dsc_123')
        self.assertEqual(AllowListEntry.objects.get(email='hello2@example.com').discount_id, 'dsc_123')
