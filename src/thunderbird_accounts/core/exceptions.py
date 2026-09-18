import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def drf_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Return safe JSON for exceptions raised by DRF API views."""
    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception(
        'Unhandled API exception',
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    detail = str(exc) if settings.DEBUG else 'Internal server error'
    return Response({'detail': detail}, status=500)


class UnexpectedBehaviour(Exception):
    """Raise when something weird happens,
    you should call sentry_sdk.set_context to give some context to the error"""

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return f'Unexpected Behaviour: {self.message}'
