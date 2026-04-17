from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.core.models import BaseModel


class LegalDocument(BaseModel):
    class DocumentType(models.TextChoices):
        TOS = 'tos', _('Terms of Service')
        PRIVACY = 'privacy', _('Privacy Policy')

    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    version = models.CharField(max_length=50, help_text=_('Version number of the document, e.g. "1.0"'),)
    is_current = models.BooleanField(default=False)
    content_path = models.CharField(
        max_length=255,
        help_text=_('Relative path to content directory under assets/legal/, e.g. "tos/v1.0"'),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['document_type', 'version'], name='unique_document_type_version'),
        ]
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['is_current']),
        ]

    def __str__(self):
        current = ' (current)' if self.is_current else ''
        return f'{self.get_document_type_display()} v{self.version}{current}'

    def save(self, *args, **kwargs):
        if self.is_current:
            LegalDocument.objects.filter(
                document_type=self.document_type, is_current=True,
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class LegalDocumentResponse(BaseModel):
    """Audit log of user responses (accept/decline) to legal documents."""

    class Action(models.TextChoices):
        ACCEPTED = 'accepted', _('Accepted')
        DECLINED = 'declined', _('Declined')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='legal_responses',
    )
    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.PROTECT,
        related_name='responses',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    source_context = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_('Where the user responded from, e.g. "sign-up", "dashboard", "thundermail"'),
    )

    class Meta:
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['user', 'document']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f'{self.user} {self.action} {self.document} at {self.created_at}'
