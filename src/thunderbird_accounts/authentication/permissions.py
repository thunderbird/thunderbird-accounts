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


# Re-classify log-level for some cases expected from pen-testers, but not internally.
EXPECTED_PADDLE_REJECTIONS = {
    "Unable to extract the 'Paddle-Signature' header from the request",
    'Too much time has elapsed between the request and this process',
}


class ExpectedPaddleRejectionFilter(logging.Filter):
    def filter(self, record):
        if record.getMessage() in EXPECTED_PADDLE_REJECTIONS:
            record.levelno = logging.INFO
            record.levelname = logging.getLevelName(logging.INFO)
        return True


# The "paddle_billing" namespace is used within the Paddle SDK
logging.getLogger('paddle_billing').addFilter(ExpectedPaddleRejectionFilter())


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


def user_owns_email(user, email: str) -> bool:
    """Return True if ``email`` is one of the addresses on the user's record: their username,
    account email, recovery email, or a primary/alias ``Email`` row on one of their mail accounts.
    Case-insensitive. Uses the local database only; Stalwart is not consulted."""
    from thunderbird_accounts.mail.models import Email

    if not user or not getattr(user, 'is_authenticated', False) or not email:
        return False

    email = email.strip().lower()
    own_addresses = {address.lower() for address in (user.username, user.email, user.recovery_email) if address}
    if email in own_addresses:
        return True

    return Email.objects.filter(address__iexact=email, account__user=user).exists()
