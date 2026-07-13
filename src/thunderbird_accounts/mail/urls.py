from django.urls import path

from thunderbird_accounts.mail import api, views
from thunderbird_accounts.mail.views import jmap_test_page


admin_urlpatterns = [
    path(
        'mail/admin/stalwart/',
        views.AdminStalwartList.as_view(),
        name='admin_stalwart_list',
    ),
]

middleware_exempt_urlpatterns = [
    path('appointment/caldav/setup/', views.appointment_caldav_setup, name='appointment_caldav_setup'),
    path('api/v1/mail/is-username-available/', api.is_username_available, name='api_is_username_available'),
    path(
        'api/v1/contact/check-email-is-on-allow-list/',
        api.check_email_is_on_allow_list,
        name='api_check_email_is_on_allow_list',
    ),
]

subscribed_urlpatterns = [
    path('app-passwords/set', views.app_password_set, name='app_password_set'),
    path('display-name/set', views.display_name_set, name='display_name_set'),
    path('custom-domains/add', views.create_custom_domain, name='add_custom_domain'),
    path('custom-domains/verify', views.verify_custom_domain, name='verify_custom_domain'),
    path('custom-domains/remove', views.remove_custom_domain, name='remove_custom_domain'),
    path('custom-domains/dns-records', views.get_dns_records, name='get_dns_records'),
    path('email-aliases/add', views.add_email_alias, name='add_email_alias'),
    path('email-aliases/remove', views.remove_email_alias, name='remove_email_alias'),
    path('api/v1/mail/app-passwords/set/', views.app_password_set, name='api_app_password_set'),
    path('api/v1/mail/display-name/set/', views.display_name_set, name='api_display_name_set'),
]

oidc_subscribed_urlpatterns = [
    path('test/jmap/', jmap_test_page, name='jmap-test'),
]
