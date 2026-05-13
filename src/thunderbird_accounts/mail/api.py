from thunderbird_accounts.authentication.utils import is_email_reserved, is_email_in_allow_list
from thunderbird_accounts.mail.exceptions import EmailNotValidError
from thunderbird_accounts.mail.utils import validate_email
from rest_framework.permissions import AllowAny
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


class CheckEmailIsOnAllowListThrottle(UserRateThrottle):
    scope = 'check_email_is_on_allow_list'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([UsernameAvailableThrottle])
def is_username_available(request: Request):
    username = request.data.get('username')
    if not username:
        raise ValidationError(_('You need to enter a username.'))

    full_username = f'{username}@{settings.PRIMARY_EMAIL_DOMAIN}'
    username_not_valid_err = _('This username is not valid. Try another one.')

    # Make sure they don't use a reserved word in their email
    if is_email_reserved(full_username):
        raise ValidationError(username_not_valid_err)

    try:
        validate_email(full_username, username_not_valid_err)
    except EmailNotValidError as ex:
        raise ValidationError(ex.error_message)

    user = User.objects.filter(username=full_username).first()
    if user:
        raise ValidationError(_('This username is already taken. Try another one.'))

    return Response(status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([CheckEmailIsOnAllowListThrottle])
def check_email_is_on_allow_list(request: Request):
    email = request.data.get('email')
    if not email:
        raise ValidationError(_('You need to enter an email address.'))

    return Response({
        'is_on_allow_list': is_email_in_allow_list(email),
    }, status=200)
