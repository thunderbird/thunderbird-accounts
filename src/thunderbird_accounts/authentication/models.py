import uuid

from django.conf import settings
from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

from thunderbird_accounts.utils.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    :param fxa_id: The ID of the connected firefox account
    :param last_used_email: The last used email associated with firefox account

    :param display_name: Display name from FxA profile
    :param avatar_url: Avatar URL from FxA profile
    :param timezone: The user's timezone
    """
    fxa_id = models.CharField(max_length=256, null=True)
    last_used_email = models.CharField(max_length=256, null=True)

    # FXA profile information
    display_name = models.CharField(max_length=256, null=True)
    avatar_url = models.CharField(max_length=2048, null=True)
    timezone = models.CharField(max_length=128, default='UTC')

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
