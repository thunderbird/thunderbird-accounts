from django.contrib import admin

from thunderbird_accounts.core.models import ZendeskAgentConnection


@admin.register(ZendeskAgentConnection)
class ZendeskAgentConnectionAdmin(admin.ModelAdmin):
    list_display = ('zendesk_user_email', 'zendesk_user_id', 'zendesk_subdomain', 'user', 'created_at', 'updated_at')
    list_filter = ('zendesk_subdomain', 'created_at', 'updated_at')
    search_fields = ('zendesk_user_email', 'zendesk_user_id', 'user__email', 'user__username')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
