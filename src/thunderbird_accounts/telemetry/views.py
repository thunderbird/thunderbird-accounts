import base64
import hmac
import hashlib
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _verify_signature(request, secret):
    """Verify the HMAC-SHA256 signature from Stalwart's X-Signature header.

    Stalwart signs the raw request body with HMAC-SHA256 and sends the result
    standard-base64-encoded in the X-Signature header.
    """
    signature = request.headers.get('X-Signature')
    if not signature:
        return False
    expected = base64.b64encode(
        hmac.new(secret.encode('utf-8'), request.body, hashlib.sha256).digest()
    ).decode('ascii')
    return hmac.compare_digest(signature, expected)


@csrf_exempt
@require_POST
def stalwart_webhook(request):
    """Accept Stalwart telemetry webhook events and enqueue for async processing."""
    from thunderbird_accounts.telemetry.tasks import process_stalwart_events

    secret = settings.STALWART_WEBHOOK_SECRET
    if not secret and not settings.IS_DEV:
        logger.error('STALWART_WEBHOOK_SECRET not configured, rejecting webhook')
        return JsonResponse({'error': 'webhook not configured'}, status=503)
    if secret and not _verify_signature(request, secret):
        return JsonResponse({'error': 'invalid signature'}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    events = payload.get('events', [])
    if events:
        process_stalwart_events.delay(events)

    return JsonResponse({'status': 'accepted', 'events_queued': len(events)})
