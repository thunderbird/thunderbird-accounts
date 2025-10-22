from django.contrib import admin

from thunderbird_accounts.mail.admin.models import AccountAdmin
from thunderbird_accounts.mail.models import Account

# Register your models here.
admin.site.register(Account, AccountAdmin)
