from typing import Optional


class TaskFailed(Exception):
    """Raised when a needs to fail intentionally (an unrecoverable error for example.)
    Celery only seems to treat exceptions as failed tasks.
    These exceptions are ignored by Sentry in settings.

    :reason str: The reason why the task failed, should be short and sweet.
    :other dict|None: Any other data you want to stuff in there.
    """

    reason: str
    other: dict

    def __init__(self, reason: str, other: Optional[dict], *args, **kwargs):
        super().__init__(args, kwargs)
        self.reason = reason
        self.other = other or {}

    def __str__(self):
        return f'Task Failed: {self.reason}'
