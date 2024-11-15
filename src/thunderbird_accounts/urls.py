from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from thunderbird_accounts.authentication import views as auth_views
from django.utils.translation import gettext_lazy as _

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
    path('fxa', auth_views.fxa_callback, name='fxa_callback'),
    re_path(r'^favicon\.ico$', favicon_view),

    # API
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

]

if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))

# Needed with uvicorn dev server
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


