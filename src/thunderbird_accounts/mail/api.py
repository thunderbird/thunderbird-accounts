from rest_framework.permissions import AllowAny
from django.core.exceptions import ValidationError as DjValidationError
from django.core.validators import EmailValidator
from django.conf import settings
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _


from thunderbird_accounts.authentication.models import User


class UsernameAvailableThrottle(UserRateThrottle):
    scope = 'is_username_available'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([UsernameAvailableThrottle])
def is_username_available(request: Request):
    username = request.data.get('username')
    if not username:
        raise ValidationError(_('You need to enter a username.'))

    full_username = f'{username}@{settings.PRIMARY_EMAIL_DOMAIN}'
    username_not_valid_err = _('This username is not valid. Try another one.')

    # EmailValidator allows for up to 350 characters, but username is defined with max_length of 150.
    if len(username) > User.USERNAME_MAX_LENGTH:
        raise ValidationError(username_not_valid_err)

    email_validator = EmailValidator(username_not_valid_err)
    # So EmailValidator.__call__ will raise a ValidationError if it fails, but they're the wrong
    # ValidationError...So catch this ValidationError so we can raise DRF's ValidationError.
    try:
        email_validator(full_username)
    except DjValidationError as ex:
        raise ValidationError(ex.message)

    user = User.objects.filter(username=full_username).first()
    if user:
        raise ValidationError(_('This username is already taken. Try another one.'))

    return Response(status=200)
