from urllib.parse import urljoin

from django.conf import settings
from django.contrib import admin
from thunderbird_accounts.subscription.models import Subscription, Plan, SubscriptionItem, Price, Transaction, Product


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return settings.DEBUG

    def has_change_permission(self, request, obj=None):
        return settings.DEBUG

    # def has_delete_permission(self, request, obj=None):
    #    return False


class CustomReadonlyAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def view_on_site(self, obj=None):
        """Handy link to the Paddle vendor site for various Paddle models"""
        base_url = settings.PADDLE_VENDOR_SITE

        if obj is None:
            return None

        if isinstance(obj, Product):
            return urljoin(base_url, f'/products-v2/{obj.paddle_id}')
        elif isinstance(obj, Price):  # Pricing doesn't have a dedicated route, so ship 'em to products
            return urljoin(base_url, f'/products-v2/{obj.paddle_product_id}')
        elif isinstance(obj, Subscription):
            return urljoin(base_url, f'/subscriptions-v2/{obj.paddle_id}')
        elif isinstance(obj, Transaction):
            return urljoin(base_url, f'/transactions-v2/{obj.paddle_id}')

        return None


# Data stores for Paddle information
admin.site.register(Subscription, admin_class=CustomReadonlyAdmin)
admin.site.register(SubscriptionItem, admin_class=CustomReadonlyAdmin)
admin.site.register(Transaction, admin_class=CustomReadonlyAdmin)
admin.site.register(Price, admin_class=CustomReadonlyAdmin)
admin.site.register(Product, admin_class=CustomReadonlyAdmin)

admin.site.register(Plan)
