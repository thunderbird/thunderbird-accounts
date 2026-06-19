from enum import StrEnum
from urllib.parse import quote, unquote_plus
from django.conf import settings
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import AllowAny
import sentry_sdk
from thunderbird_accounts.authentication.exceptions import InvalidDomainError, ImportUserError
from thunderbird_accounts.authentication.utils import (
    is_email_in_allow_list,
    KeycloakRequiredAction,
    is_email_reserved,
    can_register_with_username,
    get_user_by_contact_email,
)
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.serializers import UserProfileSerializer


class SignUpThrottle(UserRateThrottle):
    scope = 'sign_up'


class CanISignUpThrottle(UserRateThrottle):
    scope = 'can_i_sign_up'

class CanISignUpResponses(StrEnum):
    WAIT_LIST = 'wait-list'
    LOGIN = 'login'
    SIGN_UP = 'sign-up'

@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([CanISignUpThrottle])
def can_i_sign_up(request: Request):
    """This is a temporary fix until we switch off Mailchimp automated emails..."""
    email = request.data.get('email')

    go_to = CanISignUpResponses.WAIT_LIST
    if email and not request.user.is_authenticated:
        # Remove uri encoding
        email = unquote_plus(email)

        has_an_account = get_user_by_contact_email(email)
        is_in_allow_list = is_email_in_allow_list(email)

        # Decide where the user should be sent
        if has_an_account:
            go_to = CanISignUpResponses.LOGIN
        elif is_in_allow_list:
            go_to = CanISignUpResponses.SIGN_UP


    return Response({'go_to': go_to})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([SignUpThrottle])
def sign_up(request: Request):
    """The api endpoint for signing up a new user.

    We create the Keycloak user and attach its uuid to the local Account's user object.
    We only create the local Accounts user object if the Keycloak user object was successfully created.
    """
    # This file is loaded before models are ready, so we import locally here...for now.
    from thunderbird_accounts.authentication.clients import KeycloakClient
    from thunderbird_accounts.authentication.models import AllowListEntry, User

    data = request.data

    # This email is the recovery / verification email address at this point
    email = data.get('email')

    timezone = data.get('zoneinfo') or 'UTC'
    locale = data.get('locale') or 'en'

    partial_username = data.get('partialUsername')
    username = f'{partial_username}@{settings.PRIMARY_EMAIL_DOMAIN}'

    generic_email_error = _('You cannot sign-up with that email address.')

    if not email:
        return Response({'error': generic_email_error, 'type': 'no-email'}, status=400)

    if not is_email_in_allow_list(email):
        # Redirect the user to the tbpro waitlist
        return Response(
            {
                'error': _('You are not on the allow list.'),
                'type': 'go-to-wait-list',
                'href': f'{settings.TB_PRO_WAIT_LIST_URL}?email={quote(email)}',
            },
            status=403,
        )

    # Make sure there's no email alias with this address
    if not can_register_with_username(partial_username) or is_email_reserved(username):
        return Response({'error': generic_email_error, 'type': 'username-in-use'}, status=400)

    if not data.get('password'):
        return Response(
            {'error': _('You need to enter a password to sign-up.'), 'type': 'password-is-empty'},
            status=400,
        )

    # Email gets updated in the middleware's update_user function
    # So we also save it to the recovery_email field here
    # src/thunderbird_accounts/authentication/middleware.py#L126
    user = User(
        username=username,
        email=email,
        recovery_email=email,
        display_name=username,
        language=locale,
        timezone=timezone,
    )

    # Create the user on keycloak's end
    keycloak = KeycloakClient()
    try:
        keycloak_pkid = keycloak.import_user(
            username,
            email,
            timezone=timezone,
            password=data.get('password'),
            send_action_email=KeycloakRequiredAction.VERIFY_EMAIL,
            verified_email=False,
        )

        # Save the oidc id so it matches on login
        user.oidc_id = keycloak_pkid
        user.save()

        # Tie the allow list entry with our new user
        if settings.USE_ALLOW_LIST:
            allow_list_entry = AllowListEntry.objects.get(email=email)
            allow_list_entry.user = user
            allow_list_entry.save()
    except (ValueError, InvalidDomainError, AllowListEntry.DoesNotExist):
        # Only username errors raise ValueErrors right now
        return Response(
            {
                'error': generic_email_error,
                'type': 'invalid-domain',
            },
            status=400,
        )
    except ImportUserError as ex:
        sentry_sdk.capture_exception(ex)
        return Response(
            {
                'error': ex.error_desc if ex.error_desc else _('There was an unknown error, please try again later.'),
                'type': ex.error_code if ex.error_code else 'unknown-error',
            },
            status=400 if ex.error_code else 500,
        )

    return Response({'success': True})
