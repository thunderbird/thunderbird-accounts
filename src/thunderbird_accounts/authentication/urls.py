from django.conf import settings
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from thunderbird_accounts.authentication import api, views
from thunderbird_accounts.authentication.api import (
    can_i_sign_up,
    create_test_allow_list_entry,
    get_user_profile,
    sign_up,
)


admin_urlpatterns = [
    path(
        'admin/authentication/allowlistentry-custom/import/',
        views.AdminAllowListEntryImport.as_view(),
        name='allow_list_entry_import',
    ),
    path(
        'admin/authentication/allowlistentry-custom/import/submit/',
        views.bulk_import_allow_list,
        name='allow_list_entry_import_submit',
    ),
]

middleware_exempt_urlpatterns = [
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/auth/get-profile/', get_user_profile, name='api_get_profile'),
    path('api/v1/auth/sign-up/', sign_up, name='api_sign_up'),
    path('api/v1/auth/can-i-sign-up/', can_i_sign_up, name='api_can_i_sign_up'),
    path('api/v1/auth/waffle-flags/', api.get_waffle_flags, name='api_waffle_flags'),
    path('api/v1/auth/mfa/methods/', api.get_mfa_methods, name='api_get_mfa_methods'),
    path('api/v1/auth/mfa/totp/setup/start/', api.start_totp_setup, name='api_start_totp_setup'),
    path('api/v1/auth/mfa/totp/setup/confirm/', api.confirm_totp_setup, name='api_confirm_totp_setup'),
    path(
        'api/v1/auth/mfa/totp/credentials/<str:credential_id>/',
        api.remove_totp_credential,
        name='api_remove_totp_credential',
    ),
    path(
        'api/v1/auth/mfa/recovery-codes/regenerate/',
        api.regenerate_recovery_codes,
        name='api_regenerate_recovery_codes',
    ),
    path(
        'api/v1/auth/mfa/recovery-codes/credentials/<str:credential_id>/',
        api.remove_recovery_codes_credential,
        name='api_remove_recovery_codes_credential',
    ),
    path('api/v1/testing/allow-list/', create_test_allow_list_entry, name='api_create_test_allow_list_entry'),
]

oidc_authenticated_urlpatterns = [
    path('oidc/mfa-reauth/', views.MfaReauthenticationRequestView.as_view(), name='mfa_reauth'),
    path('logout/callback', views.oidc_logout_callback, name='logout_callback'),
    path('reset-password/', views.start_reset_password_flow, name='reset_password'),
]

oidc_public_urlpatterns = [
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('logout/', views.start_oidc_logout, name='logout'),
    path('login/', lambda r: redirect(settings.LOGIN_URL), name='login'),
]
