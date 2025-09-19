from functools import cached_property

from django.conf import settings
from django.db import models

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.utils.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    :param oidc_id: The ID of the connected oidc account
    :param last_used_email: The last used email associated with this account
    :param language: The user's preferred language to view the ui/system emails in
    :param display_name: Display name from oidc profile
    :param avatar_url: Avatar URL from oidc profile
    :param timezone: The user's timezone
    """

    class UserLanguageType(models.TextChoices):
        ENGLISH = 'en', _('English')
        GERMAN = 'de', _('German')

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer."
        ),
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )

    oidc_id = models.CharField(max_length=256, null=True, help_text=_("OIDC's UID field"))
    last_used_email = models.CharField(max_length=256, null=True, help_text=_('The email previously used to login'))
    language = models.CharField(
        max_length=16,
        choices=UserLanguageType,
        default=UserLanguageType.ENGLISH,
        help_text=_('The language the UI and system emails will display in'),
    )

    # profile information
    display_name = models.CharField(max_length=256, null=True, help_text=_('The display name'))
    avatar_url = models.CharField(max_length=2048, null=True, help_text=_('The avatar url'))
    timezone = models.CharField(max_length=128, default='UTC', help_text=_("The user's timezone"))

    is_test_account = models.BooleanField(
        _('Test Account'), default=False, help_text=_('Whether this account is used for testing.')
    )

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['timezone']),
        ]

    def has_usable_password(self):
        """Disable passwords for oidc"""
        if settings.AUTH_SCHEME == 'oidc':
            return False
        return super().has_usable_password()

    def get_short_name(self):
        return self.display_name

    @cached_property
    def has_active_subscription(self):
        from thunderbird_accounts.subscription.models import Subscription

        return self.subscription_set.filter(status=Subscription.StatusValues.ACTIVE).count() > 0

    @cached_property
    def stalwart_primary_email(self) -> str | None:
        """Returns the primary email address used for Stalwart."""
        account = self.account_set.first()
        if account:
            email = account.email_set.filter(type=account.email_set.model.EmailType.PRIMARY).first()
            return email.address if email else None
        return None
