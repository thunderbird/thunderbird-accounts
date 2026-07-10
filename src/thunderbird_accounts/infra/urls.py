from django.urls import path

from thunderbird_accounts.infra import views


public_urlpatterns = [
    path('health', views.health_check),
]
