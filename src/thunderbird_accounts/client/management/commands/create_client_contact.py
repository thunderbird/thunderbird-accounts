"""
Create a new Client Contact from a given Client UUID.
"""

from django.core.management.base import BaseCommand
from thunderbird_accounts.client import models


class Command(BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py create_client_contact <client_uuid> <contact_name> <contact_email> <contact_url>

    """

    help = 'Creates a client contact'

    def add_arguments(self, parser):
        parser.add_argument('client_uuid', type=str, help='UUID of the client this contact connects to')
        parser.add_argument('contact_name', type=str, help='Contact name for the client')
        parser.add_argument('contact_email', type=str, help='Contact email for the client')
        parser.add_argument('contact_url', type=str, help='Contact website for the client')

    def handle(self, *args, **options):
        client_uuid = options.get('client_uuid')

        try:
            client = models.Client.objects.get(uuid=client_uuid)
        except models.Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Client: {client_uuid} does not exist'))
            return

        existing_contact = models.ClientContact.objects.filter(email=options.get('contact_email')).first()
        if existing_contact:
            self.stdout.write(self.style.ERROR(f'A client contact with identical details already exists for client {client_uuid}'))
            return

        models.ClientContact.objects.create(
            client_id=client.uuid,
            name=options.get('contact_name'),
            email=options.get('contact_email'),
            website=options.get('contact_url'),
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created client contact {options.get('contact_name')} for {client.uuid}')
        )
