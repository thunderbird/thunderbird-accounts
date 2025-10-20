from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect

from thunderbird_accounts.authentication.utils import create_aia_url, KeycloakRequiredAction


@login_required
def start_reset_password_flow(request: HttpRequest):
    """Generates a url and redirects the user to an app initiated action that will start a flow to
    update their password."""
    return HttpResponseRedirect(create_aia_url(KeycloakRequiredAction.UPDATE_PASSWORD))
