from django.apps import AppConfig


class ClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'thunderbird_accounts.client'
    verbose_name = 'Client'
