from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.mail.admin.actions import admin_fix_stalwart_ids
from thunderbird_accounts.mail.admin.forms import CustomEmailBaseForm, CustomAccountBaseForm
from thunderbird_accounts.mail.models import Email, Domain


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

    search_fields = ('name',)
    search_help_text = _('Search accounts by name.')
    list_filter = ['created_at', 'updated_at']
    list_display = (
        'name',
        'quota',
        'user',
        'created_at',
        'updated_at',
    )


class DomainAdmin(admin.ModelAdmin):
    actions = [admin_fix_stalwart_ids]

    model = Domain
    readonly_fields = ('uuid', 'stalwart_id', 'stalwart_created_at', 'stalwart_updated_at')

    search_fields = ('name',)
    search_help_text = _('Search domains by name.')
    list_filter = ['created_at', 'updated_at']
    list_display = (
        'name',
        'status',
        'user',
        'created_at',
        'updated_at',
    )
