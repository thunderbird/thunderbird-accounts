import sentry_sdk
from django.contrib import messages, admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.admin.actions import (
    admin_fix_broken_stalwart_account,
    admin_sync_plan_to_keycloak,
    admin_manual_activate_subscription_features,
)
from thunderbird_accounts.authentication.admin.forms import CustomUserChangeForm, CustomNewUserForm
from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import DeleteUserError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient


class CustomUserAdmin(UserAdmin):
    @admin.display(description='Plan')
    def shorten_plan(user: User) -> str:
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
        has_errors = False
        if obj.oidc_id:
            # Delete the user on keycloak's end
            keycloak = KeycloakClient()
            try:
                keycloak.delete_user(obj.oidc_id)
            except DeleteUserError as ex:
                has_errors = True
                sentry_sdk.capture_exception(ex)
                messages.add_message(
                    request,
                    messages.ERROR,
                    _(
                        f'Could not delete {obj.email} from <b>Keycloak</b>. '
                        f"You'll need to clean that up yourself. Error: {ex}"
                    ),
                )

            # Delete the stalwart email too!
            if obj.stalwart_primary_email:
                stalwart = MailClient()
                try:
                    stalwart.delete_account(obj.stalwart_primary_email)
                except Exception as ex:
                    has_errors = True
                    sentry_sdk.capture_exception(ex)
                    messages.add_message(
                        request,
                        messages.ERROR,
                        _(
                            f'Could not delete {obj.username} from <b>Stalwart</b>. '
                            f"You'll need to clean that up yourself. Error: {ex}"
                        ),
                    )

        if has_errors:
            # This is the only place we can flash messages as we have access to request!
            messages.add_message(
                request,
                messages.WARNING,
                _('One or more delete requests failed. Please review the error messages and clean up accordingly.'),
            )
        # Finally delete the rest of the model
        super().delete_model(request, obj)
