from django.contrib import messages
from thunderbird_accounts.utils.types import TaskReturnStatus
from urllib.parse import urljoin

from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext_lazy as _, ngettext
from thunderbird_accounts.subscription.models import Subscription, Plan, SubscriptionItem, Price, Transaction, Product
from thunderbird_accounts.subscription.tasks import retrieve_and_update_localized_subscription_price

@admin.action(description=_('Retrieve localized pricing / discount information (#430)'))
def admin_retrieve_missing_localized_pricing_and_discounts(modeladmin, request, queryset):
    """Queries Paddle for any missing localized pricing or discounts"""
    success = 0
    errors = 0

    for sub in queryset:
        results = retrieve_and_update_localized_subscription_price.run(sub.uuid)
        if results['task_status'] == TaskReturnStatus.SUCCESS:
            success += 1
        else:
            errors += 1

    if success:
        modeladmin.message_user(
            request,
            ngettext(
                'Retrieve %d discounts / localized price.',
                'Retrieve %d discounts / localized prices.',
                success,
            )
            % success,
            messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            ngettext(
                'Failed to retrieve %d discounts / localized price.',
                'Failed to retrieve %d discounts / localized prices.',
                errors,
            )
            % errors,
            messages.ERROR,
        )
    if sum([success, errors]) == 0:
        modeladmin.message_user(
            request,
            _('Nothing to do!'),
            messages.INFO,
        )


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

class CustomSubscriptionAdmin(CustomReadonlyAdmin):
    actions = [admin_retrieve_missing_localized_pricing_and_discounts]


# Data stores for Paddle information
admin.site.register(Subscription, admin_class=CustomSubscriptionAdmin)
admin.site.register(SubscriptionItem, admin_class=CustomReadonlyAdmin)
admin.site.register(Transaction, admin_class=CustomReadonlyAdmin)
admin.site.register(Price, admin_class=CustomReadonlyAdmin)
admin.site.register(Product, admin_class=CustomReadonlyAdmin)

admin.site.register(Plan)
