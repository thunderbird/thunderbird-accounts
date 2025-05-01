from django.views.decorators.http import require_http_methods


@require_http_methods(['POST'])
def handle_paddle_webhook():
    pass
