from django.contrib import admin

from thunderbird_accounts.mail.admin.forms import CustomEmailBaseForm
from thunderbird_accounts.mail.models import Email

class EmailInline(admin.TabularInline):
    model = Email
    extra = 1

    formset = CustomEmailBaseForm



class AccountAdmin(admin.ModelAdmin):
    inlines = (EmailInline,)
    readonly_fields = (
        'uuid',
        'stalwart_id',
        'stalwart_created_at',
        'stalwart_updated_at'
    )
