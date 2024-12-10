"""
Create a new Client Environment from a given Client UUID.
"""

from django.core.management.base import BaseCommand
from thunderbird_accounts.client import models


class Command(BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py create_client_environment <client_uuid> <env_type> <env_redirect_url> <env_allowed_hostnames>

    """

    help = 'Creates a client environment'

    def add_arguments(self, parser):
        parser.add_argument('client_uuid', type=str, help='UUID of the client this environment connects to')
        parser.add_argument('env_type', type=str, help='Environment type (e.g. dev, stage, prod)')
        parser.add_argument(
            'env_redirect_url', type=str, help='Environment redirect url (where the user goes after auth)'
        )
        parser.add_argument(
            'env_allowed_hostnames', type=str, help='Allowed hostnames (separated by commas, spaces are trimmed)'
        )

    def handle(self, *args, **options):
        client_uuid = options.get('client_uuid')

        try:
            client = models.Client.objects.get(uuid=client_uuid)
        except models.Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Client: {client_uuid} does not exist'))
            return

        models.ClientEnvironment.objects.create(
            client_id=client.uuid,
            environment=options.get('env_type'),
            redirect_url=options.get('env_redirect_url'),
            allowed_hostnames=options.get('env_allowed_hostnames'),
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created client environment {options.get('env_type')} for {client.uuid}')
        )
