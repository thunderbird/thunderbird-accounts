import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Basic information that should go on every model

    :param uuid: UUID primary key
    :param created_at: Datetime the model was created on (UTC)
    :param updated_at: Datetime the model was last updated on (UTC)
    """

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]


class ZendeskAgentConnection(BaseModel):
    """Links a signed Zendesk agent identity to a Django staff user."""

    zendesk_subdomain = models.CharField(max_length=255)
    zendesk_user_id = models.CharField(max_length=255)
    zendesk_user_email = models.EmailField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=['zendesk_subdomain', 'zendesk_user_id'],
                name='unique_zendesk_agent_connection',
            ),
        ]
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['zendesk_subdomain', 'zendesk_user_id']),
            models.Index(fields=['zendesk_user_email']),
        ]

    def __str__(self):
        return f'{self.zendesk_user_email} on {self.zendesk_subdomain} -> {self.user}'
