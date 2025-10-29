from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import quote
from django.conf import settings

from thunderbird_accounts.authentication.utils import create_aia_url, KeycloakRequiredAction
from thunderbird_accounts.utils.utils import get_absolute_url


@login_required
def start_reset_password_flow(request: HttpRequest):
    """Generates a url and redirects the user to an app initiated action that will start a flow to
    update their password."""
    return HttpResponseRedirect(create_aia_url(KeycloakRequiredAction.UPDATE_PASSWORD))


@login_required
def start_oidc_logout(request: HttpRequest):
    """Begin the OIDC logout flow without logging out the local Django session.

    We redirect the user to the OP's logout endpoint with a post-logout redirect
    back to our callback. Only after the user confirms the logout do we clear the
    local Django session in the callback view.
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
