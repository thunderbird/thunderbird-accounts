"""Celery related code, this includes any flower monitoring authentication code that may or may not exist."""
import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thunderbird_accounts.settings')

app = Celery('thunderbird_accounts')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
