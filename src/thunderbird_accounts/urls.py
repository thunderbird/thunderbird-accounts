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
from django.urls import path, include
from thunderbird_accounts.authentication import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', auth_views.fxa_start),
    # This will be auth/callback in the future.
    path('fxa', auth_views.fxa_callback),
]

if settings.DEBUG:
    urlpatterns.append(path('docs/', include('rest_framework.urls')))
