from django.contrib import admin

from thunderbird_accounts.mail.models import Account, Email


class EmailInline(admin.TabularInline):
    model = Email
    extra = 1


class AccountAdmin(admin.ModelAdmin):
    inlines = (EmailInline,)


# Register your models here.
admin.site.register(Account, AccountAdmin)
admin.site.register(Email)
