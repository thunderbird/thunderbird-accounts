from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.permissions import IsClient
from thunderbird_accounts.authentication.serializers import UserProfileSerializer
from thunderbird_accounts.authentication.utils import (
    is_email_in_allow_list,
    get_cache_allow_list_entry,
    set_cache_allow_list_entry,
)


@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)


@api_view(['POST'])
@permission_classes([IsClient])
def is_in_allow_list(request: Request):
    """Is the user in the allow list? If the client_env is public we just say yes."""
    if request.client_env and request.client_env.is_public:
        return JsonResponse({'result': True})

    email = request.data.get('email')

    if not email:
        raise ValidationError({'email': 'Please provide an email address.'})

    response = get_cache_allow_list_entry(email)

    # Check if we have their user data in accounts
    if not response:
        try:
            user = User.objects.get(email=email)
            response = user.email == email
        except User.DoesNotExist:
            pass

    # If no user data, then see if their email is on the allow list
    if not response:
        response = is_email_in_allow_list(email)

    # Cache the result for 1 day
    set_cache_allow_list_entry(email, response)

    return JsonResponse({'result': response})
