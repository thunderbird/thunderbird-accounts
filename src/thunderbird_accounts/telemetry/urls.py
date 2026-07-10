from django.urls import path

from thunderbird_accounts.telemetry import api, views


public_urlpatterns = [
    path('api/v1/telemetry/stalwart/webhook/', views.stalwart_webhook, name='stalwart_webhook'),
    path('api/v1/telemetry/event', api.capture_frontend_event, name='api_capture_frontend_event'),
]
