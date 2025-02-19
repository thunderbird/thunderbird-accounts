from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from thunderbird_accounts.authentication import views as auth_views
from thunderbird_accounts.infra import views as infra_views
from thunderbird_accounts.mail import views as mail_views
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.api import get_login_code, get_user_profile, logout_user

admin.site.site_header = _('Thunderbird Accounts Admin Panel')
admin.site.site_title = _('Thunderbird Accounts Admin Panel')
admin.site.index_title = _('Accounts Administration')

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/logout/', auth_views.fxa_logout, name='fxa_logout'),
    path('auth/<str:login_code>/', auth_views.fxa_start, name='fxa_login'),
    path('auth/<str:login_code>/?redirect_to=<str:redirect_to>', auth_views.fxa_start, name='fxa_login'),
    # This will be auth/callback in the future.
    re_path(r'^favicon\.ico$', favicon_view),

    # Test
    path('', mail_views.home),
    path('self-serve', mail_views.self_serve),

    # API
    path('api/v1/auth/fxa/callback', auth_views.fxa_callback, name='fxa_callback'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('api/v1/auth/get-login/', get_login_code, name='api_get_login'),
    path('api/v1/auth/get-profile/', get_user_profile, name='api_get_profile'),
    path('api/v1/auth/logout/', logout_user, name='api_logout'),
    path('health', infra_views.health_check)
]

if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))

# Needed with uvicorn dev server
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)