from django.http import HttpRequest
from enum import StrEnum
from typing import TypedDict

from django.contrib.sessions.backends.base import SessionBase
from django.http.request import HttpRequest as DjangoHttpRequest

from thunderbird_accounts.authentication.models import User


class GeoIPLocation(TypedDict):
    city: str | None
    state: str | None
    country_code: str | None
    continent: str | None


class GeoIPSession(TypedDict, total=False):
    ip_address: str | None
    location: GeoIPLocation | None


class AccountsHttpRequest(DjangoHttpRequest):
    """Typed HttpRequest with all the optional middleware we use."""

    # Provided by: django.contrib.sessions.middleware.SessionMiddleware
    session: SessionBase
    # Provided by: django.contrib.auth.middleware.AuthenticationMiddleware
    user: User


class TaskReturnStatus(StrEnum):
    """It's either failed or success. String value should be used under a ``task_status`` key in a return object
    for a celery task"""

    FAILED = 'failed'
    SUCCESS = 'success'


class AuthenticatedHttpRequest(HttpRequest):
    user: User
