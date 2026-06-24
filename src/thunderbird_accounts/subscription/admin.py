from django.contrib import messages
from thunderbird_accounts.core.types import TaskReturnStatus
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


class CustomPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'product_name',
        'mail_address_count',
        'mail_domain_count',
        'mail_storage_bytes',
        'send_storage_bytes',
    )
    list_select_related = ('product',)

    @admin.display(description=_('Product Name'), ordering='product__name')
    def product_name(self, obj):
        if obj.product:
            return obj.product.name
        return None


class CustomPriceAdmin(CustomReadonlyAdmin):
    list_display = (
        'name',
        'formatted_amount',
        'status',
        'billing_cycle',
    )

    @admin.display(description=_('Amount'), ordering='amount')
    def formatted_amount(self, obj):
        try:
            amount = int(obj.amount) / 100
        except (TypeError, ValueError):
            return obj.amount
        return f'{obj.currency} {amount:,.2f}'

    @admin.display(description=_('Billing Cycle'), ordering='billing_cycle_interval')
    def billing_cycle(self, obj):
        if not obj.billing_cycle_frequency or not obj.billing_cycle_interval:
            return None
        return f'{obj.billing_cycle_frequency} per {obj.get_billing_cycle_interval_display()}'


class CustomProductAdmin(CustomReadonlyAdmin):
    list_display = ('name', 'description', 'paddle_id', 'status')


class CustomSubscriptionAdmin(CustomReadonlyAdmin):
    actions = [admin_retrieve_missing_localized_pricing_and_discounts]
    search_fields = ('paddle_id', 'paddle_customer_id', 'user__username')
    search_help_text = _('Search subscriptions by Paddle subscription ID, Paddle customer ID, or email.')
    list_display = ('paddle_id', 'paddle_customer_id', 'username', 'status', 'next_billed_at')
    list_select_related = ('user',)

    @admin.display(description=_('Username'), ordering='user__username')
    def username(self, obj):
        if obj.user:
            return obj.user.username
        return None


class CustomSubscriptionItemAdmin(CustomReadonlyAdmin):
    search_fields = ('subscription__user__username',)
    search_help_text = _('Search subscription items by email.')
    list_display = (
        'uuid',
        'subscription_username',
        'price_name',
        'price_amount',
        'product_name',
    )
    list_select_related = ('subscription__user', 'price', 'product')

    @admin.display(description=_('Username'), ordering='subscription__user__username')
    def subscription_username(self, obj):
        if obj.subscription and obj.subscription.user:
            return obj.subscription.user.username
        return None

    @admin.display(description=_('Price Name'), ordering='price__name')
    def price_name(self, obj):
        if obj.price:
            return obj.price.name
        return None

    @admin.display(description=_('Price Amount'), ordering='price__amount')
    def price_amount(self, obj):
        if obj.price:
            try:
                amount = int(obj.price.amount) / 100
            except (TypeError, ValueError):
                return obj.price.amount
            return f'{obj.price.currency} {amount:,.2f}'
        return None

    @admin.display(description=_('Product Name'), ordering='product__name')
    def product_name(self, obj):
        if obj.product:
            return obj.product.name
        return None


class CustomTransactionAdmin(CustomReadonlyAdmin):
    search_fields = ('paddle_id', 'paddle_subscription_id', 'subscription__user__username')
    search_help_text = _('Search transactions by Paddle transaction ID, Paddle subscription ID, or email.')
    list_display = ('paddle_id', 'paddle_subscription_id', 'subscription_username', 'status', 'billed_at')
    list_select_related = ('subscription__user',)

    @admin.display(description=_('Username'), ordering='subscription__user__username')
    def subscription_username(self, obj):
        if obj.subscription and obj.subscription.user:
            return obj.subscription.user.username
        return None


# Data stores for Paddle information
admin.site.register(Subscription, admin_class=CustomSubscriptionAdmin)
admin.site.register(SubscriptionItem, admin_class=CustomSubscriptionItemAdmin)
admin.site.register(Transaction, admin_class=CustomTransactionAdmin)
admin.site.register(Price, admin_class=CustomPriceAdmin)
admin.site.register(Product, admin_class=CustomProductAdmin)

admin.site.register(Plan, admin_class=CustomPlanAdmin)
