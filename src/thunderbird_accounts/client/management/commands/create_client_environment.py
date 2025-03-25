"""
Create a new Client Environment from a given Client UUID.
"""

import enum

from django.core.management.base import BaseCommand
from thunderbird_accounts.client import models


class Command(BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py create_client_environment <client_uuid> <env_type> <env_redirect_url> <env_allowed_hostnames>

    """

    class ReturnCodes(enum.StrEnum):
        OK = 'OK'
        ERROR = 'ERROR'  # Generic error, shouldn't normally be set
        CLIENT_DOESNT_EXIST = 'CLIENT_DOESNT_EXIST'
        ALREADY_EXISTS = 'ALREADY_EXISTS'

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
        verbosity = options.get('verbosity', 1)
        hostnames = options.get('env_allowed_hostnames')

        hostname_list = hostnames.split(',')

        try:
            client = models.Client.objects.get(uuid=client_uuid)
        except models.Client.DoesNotExist:
            if verbosity > 0:
                self.stdout.write(self.style.ERROR(f'Client: {client_uuid} does not exist'))
            return self.ReturnCodes.CLIENT_DOESNT_EXIST.value

        existing_env = models.ClientEnvironment.objects.filter(
            environment=options.get('env_type'), redirect_url=options.get('env_redirect_url')
        ).first()
        if existing_env:
            if verbosity > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f'A client environment with identical details already exists for client {client_uuid}'
                    )
                )
            return self.ReturnCodes.ALREADY_EXISTS.value

        models.ClientEnvironment.objects.create(
            client_id=client.uuid,
            environment=options.get('env_type'),
            redirect_url=options.get('env_redirect_url'),
            allowed_hostnames=hostname_list,
        )

        if verbosity > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created client environment {options.get('env_type')} for {client.uuid}'
                )
            )

        return self.ReturnCodes.OK.value
