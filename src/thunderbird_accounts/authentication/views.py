import sentry_sdk
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required, permission_required

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import quote
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.translation import ngettext, gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from thunderbird_accounts.authentication.exceptions import (
    InvalidDomainError,
    ImportUserError,
)
from thunderbird_accounts.authentication.utils import create_aia_url, KeycloakRequiredAction, is_email_in_allow_list
from thunderbird_accounts.utils.utils import get_absolute_url


@login_required
def start_reset_password_flow(request: HttpRequest):
    """Generates a url and redirects the user to an app initiated action that will start a flow to
    update their password."""
    return HttpResponseRedirect(create_aia_url(KeycloakRequiredAction.UPDATE_PASSWORD))


def start_oidc_logout(request: HttpRequest):
    """Begin the OIDC logout flow without logging out the local Django session.

    We redirect the user to the OP's logout endpoint with a post-logout redirect
    back to our callback. Only after the user confirms the logout do we clear the
    local Django session in the callback view.

    This route does not require login due to an edge case with allow lists:
        * The user somehow creates an account that is not on the allow list
        * The user logins
        * The user hits the PermissionDenied exception and is redirected to login
        * Since Keycloak is logged in, we're immediately redirected back to Accounts
        * The user is once again hit with PermissionDenied.

    There is now logic to send a unauthenticated user with a oidc_access_token to the logout screen (this route!)
    """
    callback_url = get_absolute_url(reverse('logout_callback'))
    post_logout_redirect = quote(callback_url)

    # Build the logout URL. Keycloak accepts client_id and post_logout_redirect_uri.
    base_url = settings.OIDC_OP_AUTHORIZATION_ENDPOINT.rsplit('/protocol/', 1)[0]
    logout_endpoint = f'{base_url}/protocol/openid-connect/logout'
    redirect_url = (
        f'{logout_endpoint}?client_id={settings.OIDC_RP_CLIENT_ID}&post_logout_redirect_uri={post_logout_redirect}'
    )

    return HttpResponseRedirect(redirect_url)


@login_required
def oidc_logout_callback(request: HttpRequest):
    """Finalize logout locally after the user confirmed the logout."""
    django_logout(request)

    # Redirect to home (Vue app catch-all will render)
    return HttpResponseRedirect('/')


@sensitive_post_parameters('password', 'password-confirm')
def sign_up(request: HttpRequest):
    # This file is loaded before models are ready, so we import locally here...for now.
    from thunderbird_accounts.authentication.clients import KeycloakClient
    from thunderbird_accounts.authentication.models import AllowListEntry, User

    data = request.POST
    email = data.get('email')
    timezone = data.get('zoneinfo', 'UTC')
    locale = data.get('locale', 'en')

    partial_username = data.get('partialUsername')
    username = f'{partial_username}@{settings.PRIMARY_EMAIL_DOMAIN}'

    generic_email_error = _('You cannot sign-up with that email address.')

    if not email:
        messages.error(request, generic_email_error)
        return HttpResponseRedirect('/sign-up')

    if not is_email_in_allow_list(email):
        # Redirect the user to the tbpro waitlist
        return HttpResponseRedirect(settings.TB_PRO_WAIT_LIST_URL)

    # Make sure a user does not exist with their email address
    user = User.objects.filter(Q(email=email) | Q(username=username)).exists()
    if user:
        messages.error(request, generic_email_error)
        return HttpResponseRedirect('/sign-up')

    if any(
        [
            not data.get('password'),
            not data.get('password-confirm'),
            data.get('password') != data.get('password-confirm'),
        ]
    ):
        messages.error(request, _("Your password doesn't match the confirm password field."))
        return HttpResponseRedirect('/sign-up')

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
        messages.error(request, generic_email_error)
        return HttpResponseRedirect('/sign-up')
    except ImportUserError as ex:
        sentry_sdk.capture_exception(ex)
        messages.error(
            request, ex.error_desc if ex.error_desc else _('There was an unknown error, please try again later.')
        )
        return HttpResponseRedirect('/sign-up')

    return HttpResponseRedirect('/sign-up/complete')


@require_http_methods(['POST'])
@staff_member_required()
@permission_required('authentication.add_allowlistentry')
def bulk_import_allow_list(request: HttpRequest):
    """
    Form submit for :any:`AdminAllowListEntryImport`, will bulk import email entries.
    """
    # This file is loaded before models are ready, so we import locally here...for now.
    from thunderbird_accounts.authentication.models import AllowListEntry

    entries: str = request.POST.get('bulk-entry', '')
    # Normalize new lines (I'm not sure if this is actually needed but best to be safe here.)
    entries = entries.replace('\r\n', '\n').replace('\r', '\n')
    # Now split on new line
    split_entries: list[str] = entries.split('\n')

    dupes = []
    errors = []
    add_amount = 0

    for entry in split_entries:
        # Remove spaces
        entry = entry.strip()
        if not entry:
            continue

        try:
            validate_email(entry)
        except ValidationError:
            errors.append(f'{entry} is not a valid email address.')
            continue

        try:
            AllowListEntry.objects.get(email=entry)
            dupes.append(f'{entry} already exists in the allow list.')

            # If we didn't error out here, move onto the next one
            continue
        except AllowListEntry.DoesNotExist:
            # okie
            try:
                AllowListEntry(email=entry, user=None).save()
                add_amount += 1
            except Exception as ex:
                errors.append(f'{entry} could not be created due to: {ex}.')

    for error in errors:
        messages.error(request, error)
    for dupe in dupes:
        messages.warning(request, dupe)

    if add_amount > 0:
        messages.success(
            request,
            ngettext(
                f'Imported {add_amount} email to the allow list.',
                f'Imported {add_amount} emails to the allow list.',
                add_amount,
            ),
        )
    else:
        messages.error(request, 'Could not import any emails into the allow list.')

    return HttpResponseRedirect('/admin/authentication/allowlistentry/')


@method_decorator(never_cache, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
@method_decorator(permission_required('authentication.add_allowlistentry'), name='dispatch')
class AdminAllowListEntryImport(TemplateView):
    template_name = 'admin/authentication/allowlistentry/import.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'app_label': 'authentication', 'submit_url': reverse('allow_list_entry_import_submit')})

        return context
