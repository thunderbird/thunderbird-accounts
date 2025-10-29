"""
Stalwart models live here
Schema is based on init scripts:
https://stalw.art/docs/storage/backends/postgresql#initialization-statements
"""

from django.db import models
from django.forms import CharField
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.utils.models import BaseModel


class SmallTextField(models.TextField):
    """A TextArea field with a CharField-sized widget"""

    def formfield(self, **kwargs):
        return super(models.TextField, self).formfield(
            **{
                'form_class': CharField,
            }
        )


class BaseStalwartObject(BaseModel):
    """Models that link to Stalwart principal objects should use this as the base class"""

    stalwart_id = models.CharField(
        null=True,
        help_text=_(
            'The unique ID in Stalwart. '
            "(Note: That this isn't useful for anything besides verifying that it exists in Stalwart.",
        ),
        editable=False,
    )
    stalwart_created_at = models.DateTimeField(
        null=True,
        help_text=_('Date that this object was created by this system in Stalwart.'),
        editable=False,
    )
    stalwart_updated_at = models.DateTimeField(
        null=True,
        help_text=_('Date that this object was last updated by this system in Stalwart.'),
        editable=False,
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['stalwart_id']),
            models.Index(fields=['stalwart_created_at']),
            models.Index(fields=['stalwart_updated_at']),
        ]


class Account(BaseStalwartObject):
    """Slim representation of a Stalwart individual account (inbox)."""

    name = SmallTextField(unique=True, help_text=_('The account name (this must be unique.)'))
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    quota = models.BigIntegerField(
        null=True, help_text=_('Amount of mail storage this account has access to (in bytes).')
    )
    # TODO: Implement freeze_quota

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'Stalwart Account - {self.name}'

    def save(self, **kwargs):
        """Override save to send updates to Stalwart if the quota changes"""
        from thunderbird_accounts.subscription import utils

        previous_quota = None
        new_quota = None

        # Make sure we don't crash if this is during a create
        try:
            old_plan = Account.objects.get(pk=self.uuid)
            previous_quota = old_plan.quota
            new_quota = self.quota
        except Account.DoesNotExist:
            pass

        super().save(**kwargs)

        # Only ship the task out if the field has changed
        if self.user and previous_quota != new_quota:
            utils.update_quota_on_stalwart_account(self.user, new_quota)


class Email(BaseModel):
    """Slim representation of a Stalwart email address.
    one primary, and many aliases all connected to one account (inbox)."""

    class EmailType(models.TextChoices):
        PRIMARY = 'primary', _('Primary Email')
        ALIAS = 'alias', _('Alias Email')
        LIST = 'list', _('Mailing List')

    address = SmallTextField(help_text=_('Full email address.'), unique=True)
    type = models.TextField(
        null=True,
        choices=EmailType,
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['address']),
        ]

    def __str__(self):
        if self.type == self.EmailType.ALIAS:
            return f'Alias Address - {self.address}'
        elif self.type == self.EmailType.LIST:
            return f'Mailing List - {self.address}'
        return f'Primary Address - {self.address}'
