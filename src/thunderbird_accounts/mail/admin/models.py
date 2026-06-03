from django.contrib import admin
from django.db.models import Count
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

    search_fields = ('name', 'email__address')
    search_help_text = _('Search accounts by primary email or alias.')
    list_filter = ['created_at', 'updated_at']
    list_display = (
        'name',
        'quota',
        'email_count',
        'created_at',
        'updated_at',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(email_count=Count('email'))

    @admin.display(description=_('Email Count'), ordering='email_count')
    def email_count(self, obj):
        return obj.email_count


class DomainAdmin(admin.ModelAdmin):
    actions = [admin_fix_stalwart_ids]

    model = Domain
    readonly_fields = ('uuid', 'stalwart_id', 'stalwart_created_at', 'stalwart_updated_at')

    search_fields = ('name', 'user__username')
    search_help_text = _('Search domains by name or user email.')
    list_filter = ['created_at', 'updated_at']
    list_display = (
        'name',
        'status',
        'user',
        'created_at',
        'updated_at',
    )
