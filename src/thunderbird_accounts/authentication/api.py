from django.conf import settings
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import AllowAny
import sentry_sdk
from thunderbird_accounts.authentication.exceptions import InvalidDomainError, ImportUserError
from thunderbird_accounts.authentication.utils import is_email_in_allow_list, KeycloakRequiredAction
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import ngettext, gettext_lazy as _

from thunderbird_accounts.authentication.serializers import UserProfileSerializer


class SignUpThrottle(UserRateThrottle):
    scope = 'sign_up'


@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([SignUpThrottle])
def sign_up(request: Request):
    """POST endpoint for the Accounts hosted sign up form.
    The frontend files technically live in Keycloak's vue app but are imported by Accounts so we can call this endpoint.
    (See `https://pro-services-docs.thunderbird.net/en/latest/sign-up.html`_ for more details.)

    We create the Keycloak user and attach its uuid to the local Account's user object.
    We only create the local Accounts user object if the Keycloak user object was successfully created.
    """
    # This file is loaded before models are ready, so we import locally here...for now.
    from thunderbird_accounts.authentication.clients import KeycloakClient
    from thunderbird_accounts.authentication.models import AllowListEntry, User
    from thunderbird_accounts.mail.utils import is_address_taken
    return Response({})

    data = request.data
    email = data.get('email')
    timezone = data.get('zoneinfo', 'UTC')
    locale = data.get('locale', 'en')
    print('->', email)

    partial_username = data.get('partialUsername')
    username = f'{partial_username}@{settings.PRIMARY_EMAIL_DOMAIN}'

    generic_email_error = _('You cannot sign-up with that email address.')

    request.session['form_data'] = {
        'username': username,
        'email': email,
    }

    if not email:
        return Response(
            {
                'error': generic_email_error,
                'type': 1,
            }
        )
        # return HttpResponseRedirect('/sign-up')

    if not is_email_in_allow_list(email):
        # Redirect the user to the tbpro waitlist
        return Response({'error': 'no'})
        # return HttpResponseRedirect(f'{settings.TB_PRO_WAIT_LIST_URL}?email={quote(email)}')

    # Make sure there's no email alias with this address
    if is_address_taken(username):
        return Response(
            {
                'error': generic_email_error,
                'type': 2,
            }
        )
        # return HttpResponseRedirect('/sign-up')

    if not data.get('password'):
        return Response({'error': _("Your password doesn't match the confirm password field.")})
        # return HttpResponseRedirect('/sign-up')

    user = User(username=username, email=email, display_name=username, language=locale, timezone=timezone)

    # TODO: Move this to a task!

    # Create the user on keycloak's end
    keycloak = KeycloakClient()
    try:
        keycloak_pkid = keycloak.import_user(
            username,
            email,
            timezone,
            password=data.get('password'),
            send_action_email=KeycloakRequiredAction.VERIFY_EMAIL,
            verified_email=False,
        )

        # Save the oidc id so it matches on login
        user.oidc_id = keycloak_pkid
        user.save()

        # Tie the allow list entry with our new user
        allow_list_entry = AllowListEntry.objects.get(email=email)
        allow_list_entry.user = user
        allow_list_entry.save()
    except (ValueError, InvalidDomainError):
        # Only username errors raise ValueErrors right now
        return Response(
            {
                'error': generic_email_error,
                'type': 3,
            }
        )
        # return HttpResponseRedirect('/sign-up')
    except ImportUserError as ex:
        sentry_sdk.capture_exception(ex)
        return Response(
            {'error': ex.error_desc if ex.error_desc else _('There was an unknown error, please try again later.')}
        )
        # return HttpResponseRedirect('/sign-up')

    # Clear form_data on success
    request.session['form_data'] = {}

    return Response({})
    # return HttpResponseRedirect('/sign-up/complete')
