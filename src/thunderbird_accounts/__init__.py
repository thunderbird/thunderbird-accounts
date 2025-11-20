"""The main module representing the Thunderbird Accounts platform."""

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.utils.translation import gettext_lazy as _

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ['celery_app']


class AccountsAdminConfig(AdminConfig):
    default_site = 'thunderbird_accounts.AccountsAdminSite'


class AccountsAdminSite(admin.AdminSite):
    site_header = _('Thunderbird Accounts Admin Panel')
    site_title = _('Thunderbird Accounts Admin Panel')
    index_title = _('Accounts Administration')

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request)
        app_list += [
            {
                'name': 'Stalwart 🌐',
                'app_label': 'stalwart',
                'models': [
                    {
                        'name': 'Principals',
                        'object_name': 'principals',
                        'admin_url': '/mail/admin/stalwart/',
                        'view_only': True,
                    }
                ],
            },
        ]
        return app_list
