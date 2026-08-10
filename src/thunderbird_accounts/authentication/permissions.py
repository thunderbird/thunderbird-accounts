from rest_framework.permissions import BasePermission
import logging


from rest_framework.authentication import BaseAuthentication

from django.conf import settings
from thunderbird_accounts.authentication.models import User

# We don't want hard requirements on having paddle package installed
try:
    from paddle_billing.Notifications import Verifier, Secret
except ImportError:
    Verifier, Secret = None, None


EXPECTED_PADDLE_REJECTIONS = {
    "Unable to extract the 'Paddle-Signature' header from the request",
    'Too much time has elapsed between the request and this process',
}


class IsValidPaddleWebhook(BaseAuthentication):
    def authenticate(self, request):
        if not Verifier or not Secret:
            logging.error('Paddle package is not installed. This webhook has been rejected.')
            return None

        try:
            integrity_check = Verifier().verify(request, Secret(settings.PADDLE_WEBHOOK_KEY))
        except Exception as exception:
            if str(exception) in EXPECTED_PADDLE_REJECTIONS:
                logging.info(str(exception))
                return None
            raise

        if not integrity_check:
            return None

        # We need to return a user, but we don't need the user for these requests
        # So return an empty user object
        return User(), None


class CanCreateTestAllowListEntries(BasePermission):
    """
    Allows access to authenticated users with the create_test_entry_via_api permission
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm('authentication.create_test_entry_via_api')
        )
