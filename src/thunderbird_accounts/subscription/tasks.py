from celery import shared_task


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def paddle_transaction_created():
    pass
