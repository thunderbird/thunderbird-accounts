from django.urls import path

from thunderbird_accounts.support import views
from thunderbird_accounts.support.customer import support_customer_api


middleware_exempt_urlpatterns = [
    path('api/v1/support/customer/', support_customer_api, name='api_support_customer'),
    path('contact/fields', views.contact_fields, name='contact_fields'),
    path('contact/submit', views.contact_submit, name='contact_submit'),
]
