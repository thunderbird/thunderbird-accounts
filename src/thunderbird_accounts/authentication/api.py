from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication import utils
from thunderbird_accounts.authentication.permissions import IsClient


@api_view(['POST'])
@permission_classes([IsClient])
def get_login_code(request: Request):
    client_env = request.client_env
    return JsonResponse(
        {
            'login': utils.create_login_code(client_env),
        }
    )
