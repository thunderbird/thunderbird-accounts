from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = 'Generate a key of 32 url-safe base64-encoded bytes.'

    def handle(self, *args, **options):
        key = Fernet.generate_key()
        self.stdout.write(self.style.SUCCESS(key.decode('utf-8')))
