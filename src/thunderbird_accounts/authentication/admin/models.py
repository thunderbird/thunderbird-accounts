from django.contrib import messages, admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.admin.actions import (
    admin_fix_broken_stalwart_account,
    admin_sync_plan_to_keycloak,
    admin_manual_activate_subscription_features,
    admin_add_to_mailchimp_list,
    admin_reset_totp_credentials,
)
from thunderbird_accounts.authentication.admin.forms import CustomUserChangeForm, CustomNewUserForm
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import delete_user_data


class CustomUserAdmin(UserAdmin):
    @admin.display(description='Plan')
    def shorten_plan(user: User) -> str | None:
        if not user.plan:
            return None
        return user.plan.name

    list_display = (
        'uuid',
        'oidc_id',
        shorten_plan,
        *UserAdmin.list_display,
        'is_test_account',
        'last_used_email',
        'recovery_email',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (None, {'fields': ('uuid', 'username')}),
        (
            _('Keycloak Account info'),
            {'fields': ('oidc_id',)},
        ),
        (
            _('Paddle Account info'),
            {
                'description': _(
                    '<b>Note</b>: Paddle Account information is automatically set / unset via webhooks from Paddle.'
                    '<br/>'
                    'If you adjust it here it may change in the future!'
                ),
                'fields': (
                    'plan',
                    'is_awaiting_payment_verification',
                ),
            },
        ),
        (_('Profile Info'), {'fields': ('display_name', 'avatar_url', 'timezone')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'is_test_account',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
    )
    readonly_fields = UserAdmin.readonly_fields + (
        'uuid',
        'display_name',
        'avatar_url',
        'created_at',
        'updated_at',
    )
    actions = [
        admin_fix_broken_stalwart_account,
        admin_sync_plan_to_keycloak,
        admin_manual_activate_subscription_features,
        admin_add_to_mailchimp_list,
        admin_reset_totp_credentials,
    ]
    list_filter = ['is_staff', 'is_superuser', 'is_test_account', 'is_active', 'plan']

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
        errors = delete_user_data(obj)

        if errors:
            for error in errors:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _(f"You'll need to clean this up yourself. Error: {error}"),
                )
            messages.add_message(
                request,
                messages.WARNING,
                _('One or more delete requests failed. Please review the error messages and clean up accordingly.'),
            )


class AllowListEntryAdmin(admin.ModelAdmin):
    search_fields = ('email',)
    search_help_text = _('Search the allow list by email address.')
    list_filter = ['created_at', 'updated_at']
    list_display = (
        'email',
        'discount_id',
        'user',
        'created_at',
        'updated_at',
    )


class LogEntryAdmin(admin.ModelAdmin):
    """Allows Admin Log entries to be shown in the django admin panel"""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        """Only show view permissinos to users with superuser and staff flags"""
        if not request.user:
            return False
        if not request.user.is_superuser or not request.user.is_staff:
            return False
        return True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('content_type')
