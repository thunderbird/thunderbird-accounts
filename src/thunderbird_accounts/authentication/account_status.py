"""Determine a user's access to Thundermail services

Two related flags matter:

* ``User.is_active`` is the staff kill switch. When it is False the user cannot sign in anywhere and every
  service is locked.
* The subsciption status grants the services. Without an active subscription the user can still sign in,
  for example to fix payment, but the services are locked.

Each external service is an ``AccountStatusHandler`` listed in ``settings.USER_ACCOUNT_STATUS_HANDLERS``. To add a
service: subclass the handler in that service's app, keep ``sync`` idempotent, and append the dotted path to the
setting.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import sentry_sdk
from django.conf import settings
from django.utils.module_loading import import_string

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.subscription.models import Subscription


@dataclass(frozen=True)
class UserAccess:
    """What a user should currently be able to do."""

    can_sign_in: bool
    has_services: bool


class AccountStatusHandler(ABC):
    """sync user access ``UserAccess`` into an external service."""

    label: str

    @abstractmethod
    def sync(self, user: User, access: UserAccess) -> None:
        """Apply ``access`` to the service. Must be idempotent, a no-op when the user has no identity on the
        service, and raise on failure."""


def user_access(user: User) -> UserAccess:
    is_active = User.objects.filter(pk=user.pk, is_active=True).exists()
    entitled = Subscription.objects.filter(user=user, status__in=Subscription.ENTITLED_STATUSES).exists()
    return UserAccess(can_sign_in=is_active, has_services=is_active and entitled)


def get_account_status_handlers() -> list[AccountStatusHandler]:
    # Resolved per call so tests can override
    return [import_string(path)() for path in settings.USER_ACCOUNT_STATUS_HANDLERS]


def sync_user_access(user: User) -> list[str]:
    """Apply ``user_access(user)`` to every handler, in the configured order.

    A failing handler does not stop the others. Failures are sent to Sentry and returned as messages so the caller
    can surface them;
    """
    access = user_access(user)
    errors = []

    for handler in get_account_status_handlers():
        try:
            handler.sync(user, access)
        except Exception as ex:
            sentry_sdk.capture_exception(ex)
            errors.append(f'{handler.label}: {ex}')

    if errors:
        logging.warning(f'[sync_user_access] user {user.uuid} {access} had errors: {errors}')

    return errors


def set_user_active(user: User, active: bool) -> list[str]:
    """Persist ``is_active`` and update services to refoect it. Returns the handler error messages."""
    user.is_active = active
    user.save(update_fields=['is_active', 'updated_at'])
    return sync_user_access(user)
