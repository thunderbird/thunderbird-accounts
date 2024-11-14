"""
Stalwart models live here
Schema is based on init scripts:
https://stalw.art/docs/storage/backends/postgresql#initialization-statements
"""
import uuid

from django.db import models
from django.db.models import UniqueConstraint, Field
from django.forms import Textarea, CharField
from django.utils.translation import gettext_lazy as _


class SmallTextField(models.TextField):
    """A TextArea field with a CharField-sized widget"""
    def formfield(self, **kwargs):
        return super(models.TextField, self).formfield(
            **{
                "form_class": CharField,
            }
        )


class Account(models.Model):
    """The Stalwart account model"""
    class AccountType(models.TextChoices):
        INDIVIDUAL = 'individual', _('Individual')
        GROUP = 'group', _('Group')

    name = SmallTextField(unique=True, help_text=_('The account name (this must be unique.)'))
    description = models.TextField(null=True, help_text=_('The account description (used in groups.)'))
    secret = models.TextField(null=True, help_text=_("""Text area of account secrets (password, app password, etc...)<br/>
    App Passwords must be in the format of <pre>$app$app_password_name$hashed_app_password</pre><br/>
    So with a password of test it could be: <pre>$app$Thunderbird$(hashed password goes here)</pre>"""))
    type = models.TextField(
        choices=AccountType
    )
    quota = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    django_pk = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        if self.type == self.AccountType.GROUP:
            return f'Account Group - {self.name}'
        return f'Account - {self.name}'


class GroupMember(models.Model):
    name = models.ForeignKey(Account, on_delete=models.CASCADE, db_column='name', to_field='name')
    member_of = models.TextField(help_text="The name of a group account (an account with the type of <b>group</b>.)")
    django_pk = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    UniqueConstraint(fields=['name', 'member_of'], name='name__member_of_pk')

    class Meta:
        indexes = [
            models.Index(fields=['name', 'member_of']),
        ]

    def __str__(self):
        return f'Group Member - {self.name} is member of {self.member_of}'

class Email(models.Model):
    class EmailType(models.TextChoices):
        PRIMARY = 'primary', _('Primary Email')
        ALIAS = 'alias', _('Alias Email')
        LIST = 'list', _('Mailing List')

    name = models.ForeignKey(Account, on_delete=models.CASCADE, db_column='name', to_field='name')
    address = SmallTextField(help_text=_('Full email address.'))
    type = models.TextField(
        null=True,
        choices=EmailType,
    )
    django_pk = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    UniqueConstraint(fields=['name', 'address'], name='name__address_pk')

    class Meta:
        indexes = [
            models.Index(fields=['name', 'address']),
        ]

    def __str__(self):
        if self.type == self.EmailType.ALIAS:
            return f'Alias Address - {self.address}'
        elif self.type == self.EmailType.LIST:
            return f'Mailing List - {self.address}'
        return f'Primary Address - {self.address}'