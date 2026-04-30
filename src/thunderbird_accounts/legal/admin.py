from django.contrib import admin

from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'version', 'is_current', 'created_at')
    list_filter = ('document_type', 'is_current')
    search_fields = ('version',)
    ordering = ('-created_at',)


@admin.register(LegalDocumentResponse)
class LegalDocumentResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'document', 'action', 'source_context', 'created_at')
    list_filter = ('action', 'document__document_type', 'source_context')
    search_fields = ('user__email', 'user__username')
    ordering = ('-created_at',)
    raw_id_fields = ('user', 'document')
