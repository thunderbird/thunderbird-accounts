import uuid
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

