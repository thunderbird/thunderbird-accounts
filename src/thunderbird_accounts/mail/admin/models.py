from django.contrib import admin

from thunderbird_accounts.mail.admin.actions import admin_fix_stalwart_ids
from thunderbird_accounts.mail.admin.forms import CustomEmailBaseForm, CustomAccountBaseForm
from thunderbird_accounts.mail.models import Email


class EmailInline(admin.TabularInline):
    model = Email
    extra = 1

    formset = CustomEmailBaseForm


class AccountAdmin(admin.ModelAdmin):
    actions = [admin_fix_stalwart_ids]

    form = CustomAccountBaseForm
    add_form = CustomAccountBaseForm

    inlines = (EmailInline,)
    readonly_fields = ('uuid', 'stalwart_id', 'stalwart_created_at', 'stalwart_updated_at')
