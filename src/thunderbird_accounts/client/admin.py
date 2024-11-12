from django.contrib import admin

from thunderbird_accounts.client.models import Client, ClientContact, ClientEnvironment, ClientWebhook


class ClientContactInline(admin.TabularInline):
    model = ClientContact
    extra = 1


class ClientEnvironmentInline(admin.TabularInline):
    model = ClientEnvironment
    extra = 1
    fields = ('environment', 'redirect_url')


class ClientAdmin(admin.ModelAdmin):
    inlines = (
        ClientContactInline,
        ClientEnvironmentInline,
    )


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientContact)
admin.site.register(ClientEnvironment)
admin.site.register(ClientWebhook)
