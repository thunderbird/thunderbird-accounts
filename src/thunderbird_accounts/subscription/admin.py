from django.contrib import admin
from thunderbird_accounts.subscription.models import Subscription, Customer

admin.site.register(Customer)
admin.site.register(Subscription)
