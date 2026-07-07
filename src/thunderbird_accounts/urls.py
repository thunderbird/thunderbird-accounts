"""
Thunderbird Accounts Urls
-------------------------

These are the routes and some light admin panel customization are located.
"""

from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from thunderbird_accounts.authentication import api as auth_api, views as auth_views
from thunderbird_accounts.core import views as core_views
from thunderbird_accounts.infra import views as infra_views
from thunderbird_accounts.mail import views as mail_views, api as mail_api
from thunderbird_accounts.mail.views import jmap_test_page
from thunderbird_accounts.subscription import views as subscription_views
from thunderbird_accounts.support import views as support_views
from thunderbird_accounts.support.customer import support_customer_api

from thunderbird_accounts.authentication.api import (
    get_user_profile,
    sign_up,
    can_i_sign_up,
    create_test_allow_list_entry,
)
from thunderbird_accounts.legal import views as legal_views
from thunderbird_accounts.telemetry import views as telemetry_views, api as telemetry_api

# Error handler overrides
handler500 = 'thunderbird_accounts.core.views.handle_500'

urlpatterns = [
    # Custom admin routes need to be before admin.site.urls
    path(
        'admin/authentication/allowlistentry-custom/import/',
        auth_views.AdminAllowListEntryImport.as_view(),
        name='allow_list_entry_import',
    ),
    path(
        'admin/authentication/allowlistentry-custom/import/submit/',
        auth_views.bulk_import_allow_list,
        name='allow_list_entry_import_submit',
    ),
    path('admin/', admin.site.urls),
    # Django-specific routes (not handled by Vue)
    path('contact/fields', support_views.contact_fields, name='contact_fields'),
    # Post only
    path('contact/submit', support_views.contact_submit, name='contact_submit'),
    path('app-passwords/set', mail_views.app_password_set, name='app_password_set'),
    path('display-name/set', mail_views.display_name_set, name='display_name_set'),
    path('custom-domains/add', mail_views.create_custom_domain, name='add_custom_domain'),
    path('custom-domains/verify', mail_views.verify_custom_domain, name='verify_custom_domain'),
    path('custom-domains/remove', mail_views.remove_custom_domain, name='remove_custom_domain'),
    path('custom-domains/dns-records', mail_views.get_dns_records, name='get_dns_records'),
    path('email-aliases/add', mail_views.add_email_alias, name='add_email_alias'),
    path('email-aliases/remove', mail_views.remove_email_alias, name='remove_email_alias'),
    # Subscription
    path('subscription/paddle/complete/', subscription_views.paddle_transaction_complete, name='paddle_completed'),
    # CalDAV auto-setup for Appointment
    path('appointment/caldav/setup/', mail_views.appointment_caldav_setup, name='appointment_caldav_setup'),
    # API
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/auth/get-profile/', get_user_profile, name='api_get_profile'),
    path('api/v1/auth/sign-up/', sign_up, name='api_sign_up'),
    path('api/v1/auth/can-i-sign-up/', can_i_sign_up, name='api_can_i_sign_up'),
    path('api/v1/auth/waffle-flags/', auth_api.get_waffle_flags, name='api_waffle_flags'),
    path('api/v1/auth/mfa/methods/', auth_api.get_mfa_methods, name='api_get_mfa_methods'),
    path('api/v1/auth/mfa/totp/setup/start/', auth_api.start_totp_setup, name='api_start_totp_setup'),
    path('api/v1/auth/mfa/totp/setup/confirm/', auth_api.confirm_totp_setup, name='api_confirm_totp_setup'),
    path(
        'api/v1/auth/mfa/totp/credentials/<str:credential_id>/',
        auth_api.remove_totp_credential,
        name='api_remove_totp_credential',
    ),
    path(
        'api/v1/auth/mfa/recovery-codes/regenerate/',
        auth_api.regenerate_recovery_codes,
        name='api_regenerate_recovery_codes',
    ),
    path(
        'api/v1/auth/mfa/recovery-codes/credentials/<str:credential_id>/',
        auth_api.remove_recovery_codes_credential,
        name='api_remove_recovery_codes_credential',
    ),
    path('api/v1/support/customer/', support_customer_api, name='api_support_customer'),
    path('api/v1/legal/current/', legal_views.get_current_legal_docs, name='legal_current'),
    path('api/v1/legal/accept/', legal_views.accept_legal_docs, name='legal_accept'),
    path('api/v1/legal/decline/', legal_views.decline_legal_docs, name='legal_decline'),
    path('api/v1/subscription/paddle/webhook/', subscription_views.handle_paddle_webhook, name='paddle_webhook'),
    path('api/v1/subscription/paddle/info/', subscription_views.get_paddle_information, name='paddle_info'),
    path('api/v1/subscription/paddle/portal/', subscription_views.get_paddle_portal_link, name='paddle_portal'),
    path('api/v1/subscription/paddle/tx/set/', subscription_views.set_paddle_transaction_id, name='paddle_txid'),
    path(
        'api/v1/subscription/paddle/tx/is-done/', subscription_views.is_paddle_transaction_done, name='paddle_is_done'
    ),
    path(
        'api/v1/subscription/plan/info/', subscription_views.get_subscription_plan_info, name='subscription_plan_info'
    ),
    path('api/v1/mail/app-passwords/set/', mail_views.app_password_set, name='api_app_password_set'),
    path('api/v1/mail/display-name/set/', mail_views.display_name_set, name='api_display_name_set'),
    path('api/v1/mail/is-username-available/', mail_api.is_username_available, name='api_is_username_available'),
    path(
        'api/v1/contact/check-email-is-on-allow-list/',
        mail_api.check_email_is_on_allow_list,
        name='api_check_email_is_on_allow_list',
    ),
    # Waffle
    re_path(r'^', include('waffle.urls')),
    # Stalwart telemetry webhook
    path('api/v1/telemetry/stalwart/webhook/', telemetry_views.stalwart_webhook, name='stalwart_webhook'),
    path('api/v1/telemetry/event', telemetry_api.capture_frontend_event, name='api_capture_frontend_event'),
    # Health check
    path('health', infra_views.health_check),
    # Test routes
    path('api/v1/testing/allow-list/', create_test_allow_list_entry, name='api_create_test_allow_list_entry'),
]


if settings.AUTH_SCHEME == 'oidc':
    urlpatterns.append(path('oidc/mfa-reauth/', auth_views.MfaReauthenticationRequestView.as_view(), name='mfa_reauth'))
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))
    urlpatterns.append(path('logout/', auth_views.start_oidc_logout, name='logout'))
    urlpatterns.append(path('logout/callback', auth_views.oidc_logout_callback, name='logout_callback'))
    urlpatterns.append(path('login/', lambda r: redirect(settings.LOGIN_URL), name='login'))
    urlpatterns.append(path('reset-password/', auth_views.start_reset_password_flow, name='reset_password'))
    # Test url for ensuring jmap connection works
    urlpatterns.append(path('test/jmap/', jmap_test_page, name='jmap-test'))


if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))

urlpatterns += [
    path(
        'mail/admin/stalwart/',
        mail_views.AdminStalwartList.as_view(),
        name='admin_stalwart_list',
    ),
]

urlpatterns += [
    # Vue App catch-all: keep this last so all explicit Django routes above take precedence
    re_path(r'^.*$', core_views.home, name='vue_app'),
]
