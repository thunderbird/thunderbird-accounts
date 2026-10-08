"""
Stalwart reference models live here
"""

import logging

import sentry_sdk
from django.db import models
from django.forms import CharField
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.core.models import BaseModel


class SmallTextField(models.TextField):
    """A TextArea field with a CharField-sized widget"""

    def formfield(self, **kwargs):
        return super().formfield(
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
    verified_archive_folder = models.BooleanField(
        default=False,
        help_text=_('On login we check if they have an archive folder. If this is true that check will be skipped.'),
    )
    # TODO: Implement freeze_quota

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'Stalwart Account - {self.name}'

    def save(self, *args, **kwargs):
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

        super().save(*args, **kwargs)

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


class Domain(BaseStalwartObject):
    """Custom domain that can be used for email addresses."""

    class DomainStatus(models.TextChoices):
        PENDING = 'pending', _('Pending Verification')
        VERIFIED = 'verified', _('Verified')
        FAILED = 'failed', _('Verification Failed')

    name = SmallTextField(unique=True, help_text=_('The domain name (e.g., example.com)'))
    status = models.CharField(
        max_length=20,
        choices=DomainStatus,
        default=DomainStatus.PENDING,
        help_text=_('Current verification status of the domain'),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='domains', help_text=_('The user who owns this domain')
    )
    verified_at = models.DateTimeField(null=True, blank=True, help_text=_('Date and time when the domain was verified'))
    last_verification_attempt = models.DateTimeField(
        null=True, blank=True, help_text=_('Date and time of the last verification attempt')
    )

    def __str__(self):
        return f'{self.name} - {self.status.capitalize()}'

    def delete_external_resources(self) -> list[str]:
        """Removes everything this domain owns outside our database: the Stalwart domain principal,
        its DKIM signatures, and the hosted DKIM TXT records in Cloudflare.

        Every step is attempted regardless of earlier failures. Each failure is sent to Sentry and
        returned as a message; an empty list means a full success. The local row is left in place so
        callers can decide whether to keep it (user-facing removal) or let it cascade (account deletion).

        Works for both the legacy (Stalwart v0.15) and migrated (Stalwart v0.16 / JMAP) paths. The
        JMAP client removes DKIM signatures as part of ``delete_domain``, the legacy client does not."""
        from thunderbird_accounts.mail import tasks as mail_tasks
        from thunderbird_accounts.mail.clients import MailClient
        from thunderbird_accounts.mail.exceptions import DomainNotFoundError

        errors = []
        stalwart_client = MailClient()

        # Don't gate this on stalwart_id: migrated users get a disabled Stalwart domain at add time,
        # before the local stalwart_id is filled in on verification.
        try:
            stalwart_client.delete_domain(self.name)
        except DomainNotFoundError:
            # Legacy pending domains are only created in Stalwart on verification, so this is expected there.
            logging.info(f'[delete_external_resources] {self.name} not found in Stalwart, continuing clean up')
        except Exception as ex:
            errors.append(f'Stalwart domain {self.name}: {ex}')
            self._capture_cleanup_exception(ex, phase='delete_stalwart_domain')

        if not self.user.is_migrated:
            try:
                stalwart_client.delete_dkim(self.name)
            except Exception as ex:
                errors.append(f'Stalwart DKIM {self.name}: {ex}')
                self._capture_cleanup_exception(ex, phase='delete_dkim')

        # Hosted DKIM TXT records are published for every user, so they're always cleaned up.
        try:
            mail_tasks.delete_hosted_dkim_dns_records.delay(self.name)
        except Exception as ex:
            errors.append(f'Cloudflare {self.name}: {ex}')
            self._capture_cleanup_exception(ex, phase='delete_hosted_dkim_dns_records')

        return errors

    def _capture_cleanup_exception(self, exception: Exception, *, phase: str):
        sentry_sdk.set_context(
            'domain',
            {
                'phase': phase,
                'domain_name': self.name,
                'domain_status': self.status,
            },
        )
        sentry_sdk.capture_exception(exception)
