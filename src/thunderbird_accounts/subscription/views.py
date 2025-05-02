from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook


@api_view(['POST'])
@authentication_classes([IsValidPaddleWebhook])
def handle_paddle_webhook(request: Request):

    pass
