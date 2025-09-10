from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.admin.actions import admin_create_stalwart_account
from thunderbird_accounts.authentication.admin.forms import CustomUserChangeForm, CustomNewUserForm
from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient


class CustomUserAdmin(UserAdmin):
    list_display = ('uuid', 'oidc_id', *UserAdmin.list_display, 'last_used_email', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('uuid', 'username')}),
        (
            _('Keycloak Account info'),
            {'fields': ('oidc_id',)},
        ),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Profile Info'), {'fields': ('display_name', 'avatar_url', 'timezone')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = UserAdmin.readonly_fields + (
        'uuid',
        'display_name',
        'avatar_url',
        'oidc_id',
        'created_at',
        'updated_at',
    )
    actions = [admin_create_stalwart_account]

    form = CustomUserChangeForm
    add_form = CustomNewUserForm

    add_fieldsets = (
        (
            _('Required Fields'),
            {
                'classes': ('wide',),
                'fields': ('username', 'email', 'timezone'),
            },
        ),
        (
            _('Optional Fields'),
            {
                'classes': ('wide',),
                'fields': ('first_name', 'last_name'),
            },
        ),
    )

    def delete_queryset(self, request, queryset):
        """Given a queryset, delete it from the database."""
        for model in queryset:
            self.delete_model(request, model)

    def delete_model(self, request, obj: User):
        if obj.oidc_id:
            # Delete the user on keycloak's end
            keycloak = KeycloakClient()
            keycloak.delete_user(obj.oidc_id)

            # Delete the stalwart email too!
            if obj.stalwart_primary_email:
                stalwart = MailClient()
                stalwart.delete_account(obj.oidc_id)
        # Finally delete the rest of the model
        super().delete_model(request, obj)
