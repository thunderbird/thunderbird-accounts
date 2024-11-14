from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


class CustomUserAdmin(UserAdmin):
    list_display = ('uuid', *UserAdmin.list_display, 'fxa_id', 'last_used_email', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('uuid',)}),
        *UserAdmin.fieldsets,
        (_('Profile Info'), {'fields': ('display_name', 'avatar_url', 'timezone')}),
        (
            _('External Account info'),
            {'fields': ('fxa_id',)},
        ),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),

    )
    readonly_fields = UserAdmin.readonly_fields + ('uuid', 'display_name', 'avatar_url', 'fxa_id', 'created_at', 'updated_at')


admin.site.register(User, CustomUserAdmin)
