from django.contrib.sessions.backends.base import SessionBase
from django.http.request import HttpRequest as DjangoHttpRequest

from thunderbird_accounts.authentication.models import User


class AccountsHttpRequest(DjangoHttpRequest):
    """Typed HttpRequest with all the optional middleware we use."""

    # Provided by: django.contrib.sessions.middleware.SessionMiddleware
    session: SessionBase
    # Provided by: django.contrib.auth.middleware.AuthenticationMiddleware
    user: User
