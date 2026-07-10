"""
Thunderbird Accounts Urls
-------------------------

These are the routes and some light admin panel customization are located.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path

from thunderbird_accounts.core import views as core_views
from thunderbird_accounts.authentication import urls as authentication_urls
from thunderbird_accounts.authentication.middleware import RequiredAuth as Authz
from thunderbird_accounts.infra import urls as infra_urls
from thunderbird_accounts.legal import urls as legal_urls
from thunderbird_accounts.mail import urls as mail_urls
from thunderbird_accounts.subscription import urls as subscription_urls
from thunderbird_accounts.support import urls as support_urls
from thunderbird_accounts.telemetry import urls as telemetry_urls


def authorized_path(route, urlconf, *, required_auth: Authz, **auth_options):
    return path(route, include(urlconf), {'required_auth': required_auth, **auth_options})

# Error handler overrides
handler500 = 'thunderbird_accounts.core.views.handle_500'

authentication_urlpatterns = [
    # This custom admin route needs to be before admin.site.urls.
    authorized_path('', authentication_urls.admin_urlpatterns, required_auth=Authz.ADMIN),
    path('', include(authentication_urls.middleware_exempt_urlpatterns)),
]

mail_urlpatterns = [
    authorized_path('', mail_urls.admin_urlpatterns, required_auth=Authz.ADMIN),
    path('', include(mail_urls.middleware_exempt_urlpatterns)),
    authorized_path('', mail_urls.subscribed_urlpatterns, required_auth=Authz.ACTIVE_SUBSCRIPTION),
]

subscription_urlpatterns = [
    path('', include(subscription_urls.public_urlpatterns)),
    authorized_path(
        '',
        subscription_urls.authenticated_urlpatterns,
        required_auth=Authz.AUTHENTICATED,
    ),
    authorized_path(
        '',
        subscription_urls.paddle_portal_urlpatterns,
        required_auth=Authz.ACTIVE_SUBSCRIPTION,
        active_subscription_response_data={},
        active_subscription_status=401,
    ),
    authorized_path(
        '',
        subscription_urls.subscription_plan_info_urlpatterns,
        required_auth=Authz.ACTIVE_SUBSCRIPTION,
        active_subscription_error_message='No active subscription found',
        active_subscription_status=404,
    ),
]

if settings.AUTH_SCHEME == 'oidc':
    authentication_urlpatterns += [
        authorized_path(
            '',
            authentication_urls.oidc_authenticated_urlpatterns,
            required_auth=Authz.AUTHENTICATED,
        ),
        path('', include(authentication_urls.oidc_public_urlpatterns)),
    ]
    mail_urlpatterns.append(
        authorized_path('', mail_urls.oidc_subscribed_urlpatterns, required_auth=Authz.ACTIVE_SUBSCRIPTION)
    )

urlpatterns = [
    *authentication_urlpatterns,
    path('admin/', admin.site.urls),
    path('', include(infra_urls.public_urlpatterns)),
    authorized_path(
        '',
        legal_urls.authenticated_urlpatterns,
        required_auth=Authz.AUTHENTICATED,
    ),
    *mail_urlpatterns,
    *subscription_urlpatterns,
    path('', include(support_urls.middleware_exempt_urlpatterns)),
    path('', include(telemetry_urls.public_urlpatterns)),
    # Waffle
    re_path(r'^', include('waffle.urls')),
]


if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))

urlpatterns += [
    # Vue App catch-all: keep this last so all explicit Django routes above take precedence
    re_path(r'^.*$', core_views.home, name='vue_app'),
]
