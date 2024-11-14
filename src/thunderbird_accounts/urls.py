"""
URL configuration for thunderbird_accounts project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from thunderbird_accounts.authentication import views as auth_views
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _('Thunderbird Accounts Admin Panel')
admin.site.site_title = _('Thunderbird Accounts Admin Panel')
admin.site.index_title = _('Accounts Administration')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/logout', auth_views.fxa_logout, name='fxa_logout'),
    path('auth/<str:login_code>/', auth_views.fxa_start, name='fxa_login'),
    path('auth/<str:login_code>/?redirect_to=<str:redirect_to>', auth_views.fxa_start, name='fxa_login'),
    # This will be auth/callback in the future.
    path('fxa', auth_views.fxa_callback, name='fxa_callback'),
]

if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))
