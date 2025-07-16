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


class Account(BaseModel):
    """Slim representation of a Stalwart individual account (inbox)."""

    name = SmallTextField(unique=True, help_text=_('The account name (this must be unique.)'))
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]


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
