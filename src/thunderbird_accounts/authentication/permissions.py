import logging


from rest_framework.authentication import BaseAuthentication

from thunderbird_accounts import settings
from thunderbird_accounts.authentication.models import User

# We don't want hard requirements on having paddle package installed
try:
    from paddle_billing.Notifications import Verifier, Secret
except ImportError:
    Verifier, Secret = None, None


class IsValidPaddleWebhook(BaseAuthentication):
    def authenticate(self, request):
        if not Verifier or not Secret:
            logging.error('Paddle package is not installed. This webhook has been rejected.')
            return None

        integrity_check = Verifier().verify(request, Secret(settings.PADDLE_WEBHOOK_KEY))

        if not integrity_check:
            return None

        # We need to return a user, but we don't need the user for these requests
        # So return an empty user object
        return User(), None
