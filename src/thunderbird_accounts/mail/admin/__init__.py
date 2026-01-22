from django.contrib import admin

from thunderbird_accounts.mail.admin.models import AccountAdmin, DomainAdmin
from thunderbird_accounts.mail.models import Account, Domain

# Register your models here.
admin.site.register(Account, AccountAdmin)
admin.site.register(Domain, DomainAdmin)