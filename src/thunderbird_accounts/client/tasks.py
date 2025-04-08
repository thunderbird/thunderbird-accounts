import datetime
from uuid import UUID

import requests
from celery import shared_task

from thunderbird_accounts.client.models import ClientEnvironment, ClientWebhook
from thunderbird_accounts.client.utils import create_webhook_hash


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def _send_client_webhook(self, client_webhook: ClientWebhook, payload: dict):
    """Generic function to send a payload to a client webhook"""
    webhook_start_at = datetime.datetime.now(datetime.UTC).timestamp()

    # Not active so return some info about it for the results
    if not client_webhook.client_environment.is_active:
        return {
            'error': 'CLIENT_ENV_NOT_ACTIVE',
            'data': {
                'webhook_uuid': client_webhook.uuid,
                'env_uuid': client_webhook.client_environment.uuid,
                'timestamp': webhook_start_at,
            },
        }

    data = payload.get('data', {})

    try:
        response = requests.post(
            client_webhook.webhook_url,
            json=data,
            headers={
                **payload.get('headers', {}),
                'X-TBA-Timestamp': webhook_start_at,
                'X-TBA-Signature': create_webhook_hash(client_webhook.secret, data),
            },
        )

        response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        raise self.retry(exc=ex)

    return {'success': True, 'data': {'timestamp': webhook_start_at}}


@shared_task(bind=True)
def send_notice_of_user_deletion(self, user_uuid: UUID):
    """Notify each active client environment that we need to remove some user data"""

    client_envs = ClientEnvironment.objects.filter(is_active=True)
    for client_env in client_envs:
        webhooks = client_env.clientwebhook_set.all()
        for webhook in webhooks:
            _send_client_webhook.delay(
                webhook,
                {
                    'headers': {
                        'X-TBA-Event': 'delete-user',
                    },
                    'data': {'user_uuid': user_uuid},
                },
            )

    return {'success': True}
