from uuid import UUID

from celery import shared_task


@shared_task
def send_client_webhook(_user_uuid: UUID):
    """A stub function for send_client_webhook"""
    # Set something so we can test for its existence.
    return {'success': True}
