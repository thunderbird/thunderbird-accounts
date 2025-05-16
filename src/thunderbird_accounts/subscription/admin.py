from django.contrib import admin
from thunderbird_accounts.subscription.models import Subscription, Plan, SubscriptionItem, Price

admin.site.register(Subscription)
admin.site.register(SubscriptionItem)
admin.site.register(Plan)
admin.site.register(Price)
