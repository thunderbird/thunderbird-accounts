import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.throttling import UserRateThrottle

from thunderbird_accounts.authentication.permissions import user_owns_email
from thunderbird_accounts.authentication.utils import is_email_in_allow_list
from thunderbird_accounts.mail.utils import is_allowed_domain
from thunderbird_accounts.support.contact_form import parse_contact_payload

logger = logging.getLogger(__name__)


class ContactSubmitThrottle(UserRateThrottle):
    scope = 'contact_submit'


class CanSubmitContactRequest(BasePermission):
    """Gate the contact form on the requester address.

    An address on one of our managed domains (``ALLOWED_EMAIL_DOMAINS``) must belong to the signed-in
    user, because support replies to it land in a mailbox we host. Any other address must pass the
    allow list when ``CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS`` is on. Missing or unparsable
    payloads are allowed through so the view can return its own validation error.

    Rejections raise ``PermissionDenied`` directly so the message reaches the user; returning False for
    an anonymous request would make DRF replace it with its generic not-authenticated message.
    """

    def has_permission(self, request, view):
        try:
            email = parse_contact_payload(request).get('email')
        except ValueError:
            return True

        if not email or not isinstance(email, str):
            return True

        email = email.strip()
        normalized_email = email.lower()
        owns_email = user_owns_email(request.user, normalized_email)

        if is_allowed_domain(normalized_email):
            if not request.user.is_authenticated:
                logger.info('[contact_submit] Rejected managed-domain address from an anonymous submitter')
                raise PermissionDenied(
                    _(
                        'To contact us from your Thundermail address, please sign in. '
                        "If you can't sign in, use a different email address."
                    )
                )

            if not owns_email:
                logger.info('[contact_submit] Rejected managed-domain address not owned by user %s', request.user.uuid)
                raise PermissionDenied(
                    _(
                        "That Thundermail address isn't on your account. "
                        'Use one of your own addresses or a different email address.'
                    )
                )

        allow_list_applies = settings.CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS and not owns_email
        if allow_list_applies and not is_email_in_allow_list(email):
            raise PermissionDenied(
                _(
                    "This email address isn't linked to a Thundermail account yet, "
                    "so we can't open a support request for it."
                )
            )

        return True
