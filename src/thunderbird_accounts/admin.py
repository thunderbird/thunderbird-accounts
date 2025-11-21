"""Stores admin panel related config classes"""
from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.views import start_oidc_logout


class AccountsAdminConfig(AdminConfig):
    default_site = 'thunderbird_accounts.admin.AccountsAdminSite'


class AccountsAdminSite(admin.AdminSite):
    site_header = _('Thunderbird Accounts Admin Panel')
    site_title = _('Thunderbird Accounts Admin Panel')
    index_title = _('Accounts Administration')

    def logout(self, request, extra_context=None):
        return start_oidc_logout(request)

    def get_app_list(self, request, app_label=None):
        """We append a fake model view in the admin panel list so we can link to the stalwart principal page"""
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
