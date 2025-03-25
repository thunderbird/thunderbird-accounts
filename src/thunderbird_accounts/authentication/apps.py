from django.apps import AppConfig
from django.conf import settings
from django.core.cache import cache


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'thunderbird_accounts.authentication'
    verbose_name = 'Authentication'

    def ready(self):
        # Do not touch! This needs to be here for signals to load
        from thunderbird_accounts.authentication import signals  # noqa

        # Clear the entire cache on application restart
        # We don't do this on dev environments because this might restart
        # each time a python file is updated.
        if settings.APP_ENV != 'dev':
            cache.clear()
