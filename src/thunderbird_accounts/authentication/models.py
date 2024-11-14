import uuid

from django.conf import settings
from django.db import models

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.utils.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    :param fxa_id: The ID of the connected firefox account
    :param last_used_email: The last used email associated with firefox account

    :param display_name: Display name from FxA profile
    :param avatar_url: Avatar URL from FxA profile
    :param timezone: The user's timezone
    """
    fxa_id = models.CharField(max_length=256, null=True, help_text=_('Mozilla Account\'s UID field'))
    last_used_email = models.CharField(max_length=256, null=True, help_text=_('The email previously used to login to Mozilla Accounts'))

    # FXA profile information
    display_name = models.CharField(max_length=256, null=True, help_text=_('The display name from Mozilla Accounts'))
    avatar_url = models.CharField(max_length=2048, null=True, help_text=_('The avatar url from Mozilla Accounts'))
    timezone = models.CharField(max_length=128, default='UTC', help_text=_('The user\'s timezone'))

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['timezone']),
        ]

    def has_usable_password(self):
        """Disable passwords for fxa"""
        if settings.AUTH_SCHEME == 'fxa':
            return False
        return super(User).has_usable_password()

    def get_short_name(self):
        return self.display_name
