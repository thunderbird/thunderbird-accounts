from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication.serializers import UserProfileSerializer


@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)
