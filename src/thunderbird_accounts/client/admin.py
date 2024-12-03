from django.contrib import admin

from thunderbird_accounts.client.models import Client, ClientContact, ClientEnvironment, ClientWebhook


class ClientContactInline(admin.TabularInline):
    model = ClientContact
    extra = 1


class ClientEnvironmentInline(admin.TabularInline):
    model = ClientEnvironment
    extra = 1
    fields = ('environment', 'redirect_url', 'allowed_hostnames')


class ClientAdmin(admin.ModelAdmin):
    inlines = (
        ClientContactInline,
        ClientEnvironmentInline,
    )


class ClientEnvironmentAdmin(admin.ModelAdmin):
    pass


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientContact)
admin.site.register(ClientEnvironment, ClientEnvironmentAdmin)
admin.site.register(ClientWebhook)
