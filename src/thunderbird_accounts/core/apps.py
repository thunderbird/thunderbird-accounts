from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'thunderbird_accounts.core'
    verbose_name = 'Core'

    def ready(self):
        # Import here so Django finishes app loading before signal registration.
        from thunderbird_accounts.core.cors import register_cors_handlers

        register_cors_handlers()
