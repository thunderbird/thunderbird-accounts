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
from django.views.generic import RedirectView
from mozilla_django_oidc.views import OIDCLogoutView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from thunderbird_accounts.infra import views as infra_views
from thunderbird_accounts.mail import views as mail_views
from thunderbird_accounts.mail.views import jmap_test_page
from thunderbird_accounts.subscription import views as subscription_views
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.api import get_user_profile

admin.site.site_header = _('Thunderbird Accounts Admin Panel')
admin.site.site_title = _('Thunderbird Accounts Admin Panel')
admin.site.index_title = _('Accounts Administration')

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^favicon\.ico$', favicon_view),
    # Mail Views
    path('', mail_views.home),
    path('contact/', mail_views.contact, name='contact'),
    path('sign-up/', mail_views.sign_up, name='sign_up'),
    path('sign-up/submit', mail_views.sign_up_submit, name='sign_up_submit'),
    path('wait-list/', mail_views.wait_list),
    path('self-serve/', mail_views.self_serve_dashboard, name='self_serve_dashboard'),
    path('self-serve/account-settings', mail_views.self_serve_account_settings, name='self_serve_account_info'),
    path('self-serve/app-passwords', mail_views.self_serve_app_passwords, name='self_serve_app_password'),
    path('self-serve/subscription', mail_views.self_serve_subscription, name='self_serve_subscription'),
    path(
        'self-serve/subscription/success',
        mail_views.self_serve_subscription_success,
        name='self_serve_subscription_success',
    ),
    path('contact/fields', mail_views.contact_fields, name='contact_fields'),
    # Post only
    path('contact/submit', mail_views.contact_submit, name='contact_submit'),
    path('self-serve/app-passwords/add', mail_views.self_serve_app_password_add, name='app_password_add'),
    path('self-serve/app-passwords/remove', mail_views.self_serve_app_password_remove, name='app_password_remove'),
    # API
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/auth/get-profile/', get_user_profile, name='api_get_profile'),
    path('api/v1/subscription/paddle/webhook/', subscription_views.handle_paddle_webhook, name='paddle_webhook'),
    path('health', infra_views.health_check),
]

if settings.AUTH_SCHEME == 'oidc':
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))
    urlpatterns.append(path('logout/', OIDCLogoutView.as_view(), name='logout'))
    urlpatterns.append(path('login/', lambda r: redirect(settings.LOGIN_URL), name='login'))
    # Test url for ensuring jmap connection works
    urlpatterns.append(path('test/jmap/', jmap_test_page, name='jmap-test'))

if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))

# Needed with uvicorn dev server
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.ASSETS_ROOT)
