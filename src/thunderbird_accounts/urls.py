"""
Thunderbird Accounts Urls
-------------------------

These are the routes and some light admin panel customization are located.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from thunderbird_accounts.authentication import views as auth_views
from thunderbird_accounts.infra import views as infra_views
from thunderbird_accounts.mail import views as mail_views
from thunderbird_accounts.mail.views import jmap_test_page
from thunderbird_accounts.subscription import views as subscription_views
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.api import get_user_profile

urlpatterns = [
    path('admin/', admin.site.urls),
    # Django-specific routes (not handled by Vue)
    path('wait-list/', mail_views.wait_list),
    path('contact/fields', mail_views.contact_fields, name='contact_fields'),
    # Post only
    path('contact/submit', mail_views.contact_submit, name='contact_submit'),
    path('app-passwords/set', mail_views.app_password_set, name='app_password_set'),
    path('display-name/set', mail_views.display_name_set, name='display_name_set'),
    path('custom-domains/add', mail_views.create_custom_domain, name='add_custom_domain'),
    path('custom-domains/verify', mail_views.verify_custom_domain, name='verify_custom_domain'),
    path('custom-domains/remove', mail_views.remove_custom_domain, name='remove_custom_domain'),
    path('custom-domains/dns-records', mail_views.get_dns_records, name='get_dns_records'),
    path('email-aliases/add', mail_views.add_email_alias, name='add_email_alias'),
    path('email-aliases/remove', mail_views.remove_email_alias, name='remove_email_alias'),
    # API
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/auth/get-profile/', get_user_profile, name='api_get_profile'),
    path('api/v1/subscription/paddle/webhook/', subscription_views.handle_paddle_webhook, name='paddle_webhook'),
    path('api/v1/subscription/paddle/info', subscription_views.get_paddle_information, name='paddle_info'),
    path('api/v1/subscription/paddle/portal', subscription_views.get_paddle_portal_link, name='paddle_portal'),
    path(
        'api/v1/subscription/paddle/complete',
        subscription_views.notify_paddle_checkout_complete,
        name='paddle_complete',
    ),
    path('api/v1/subscription/plan/info', subscription_views.get_subscription_plan_info, name='subscription_plan_info'),
    path('health', infra_views.health_check),
]


if settings.AUTH_SCHEME == 'oidc':
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))
    urlpatterns.append(path('logout/', auth_views.start_oidc_logout, name='logout'))
    urlpatterns.append(path('logout/callback', auth_views.oidc_logout_callback, name='logout_callback'))
    urlpatterns.append(path('login/', lambda r: redirect(settings.LOGIN_URL), name='login'))
    urlpatterns.append(path('reset-password/', auth_views.start_reset_password_flow, name='reset_password'))
    # Test url for ensuring jmap connection works
    urlpatterns.append(path('test/jmap/', jmap_test_page, name='jmap-test'))

if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))

# Needed with uvicorn dev server
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.ASSETS_ROOT)

urlpatterns += [
    path(
        'mail/admin/stalwart/',
        mail_views.AdminStalwartList.as_view(),
        name='admin_stalwart_list',
    ),
    path(
        'mail/admin/stalwart/purge',
        mail_views.purge_stalwart_accounts,
        name='purge_stalwart_accounts',
    ),
]

urlpatterns += [
    # Vue App catch-all: keep this last so all explicit Django routes above take precedence
    re_path(r'^.*$', mail_views.home, name='vue_app'),
]
