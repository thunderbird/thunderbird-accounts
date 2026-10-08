from django.contrib import admin, messages
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.mail.admin.actions import admin_fix_stalwart_ids, admin_replace_stalwart_ids
from thunderbird_accounts.mail.admin.forms import CustomEmailBaseForm, CustomAccountBaseForm
from thunderbird_accounts.mail.models import Email, Domain


class EmailInline(admin.TabularInline):
    model = Email
    extra = 1

    formset = CustomEmailBaseForm


class AccountAdmin(admin.ModelAdmin):
    actions = [admin_fix_stalwart_ids, admin_replace_stalwart_ids]

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
        return super().get_queryset(request).annotate(email_count=Count('email', distinct=True))

    @admin.display(description=_('Email Count'), ordering='email_count')
    def email_count(self, obj):
        return obj.email_count


class DomainAdmin(admin.ModelAdmin):
    actions = [admin_fix_stalwart_ids, admin_replace_stalwart_ids]

    model = Domain
    readonly_fields = ('uuid', 'stalwart_id', 'stalwart_created_at', 'stalwart_updated_at')

    search_fields = ('name', 'user__username')
    search_help_text = _('Search domains by name or user email.')
    ordering = ('-created_at',)
    list_filter = ['status', 'created_at', 'updated_at']
    list_display = (
        'name',
        'status',
        'user',
        'created_at',
        'last_verification_attempt',
    )

    def delete_queryset(self, request, queryset):
        for domain in queryset:
            self.delete_model(request, domain)

    def delete_model(self, request, obj: Domain):
        """Mirror the user-facing removal so an admin delete doesn't leave Stalwart/Cloudflare state behind."""
        errors = obj.delete_external_resources()

        for error in errors:
            messages.add_message(
                request,
                messages.ERROR,
                _(f"You'll need to clean this up yourself. Error: {error}"),
            )
        if errors:
            messages.add_message(
                request,
                messages.WARNING,
                _('One or more delete requests failed. Please review the error messages and clean up accordingly.'),
            )

        super().delete_model(request, obj)
