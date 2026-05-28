import uuid
from thunderbird_accounts.telemetry import capture
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _


class AnalyticsThrottle(UserRateThrottle):
    scope = 'analytics'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnalyticsThrottle])
def capture_frontend_event(request: Request):
    """This function simply takes the log event,
    checks it against acceptable values and if it's valid then we log it.

    This is a fire and forget function, 
    it's not vital that they actually capture but this function should not block the frontend either."""

    event = request.data.get('event')
    event_properties = request.data.get('event_properties')
    if not event or event not in settings.FRONTEND_EVENTS:
        raise ValidationError(_('The event passed is not valid.'))

    if request.user.is_authenticated:
        capture(event, request.user.oidc_id, event_properties)
    else:
        capture(event, str(f'unauthenticated-{uuid.uuid4().hex}'), event_properties)

    return Response(status=200)
