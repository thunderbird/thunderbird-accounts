"""
Create a new Client, with a Client Contact and optionally a Client Environment.
"""

import enum

from django.core import management
from django.core.management.base import BaseCommand
from thunderbird_accounts.client import models
from thunderbird_accounts.client.management.commands import create_client_contact, create_client_environment


class Command(BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py create_client <client_name> <contact_name> <contact_email> <contact_url> [--env_type <str>] [--env_redirect_url <str>] [--env_allowed_hostnames <str>]

    """

    class ReturnCodes(enum.StrEnum):
        OK = 'OK'
        ERROR = 'ERROR'  # Generic error, shouldn't normally be set
        NOT_ENOUGH_PARAMS = 'NOT_ENOUGH_PARAMS'
        ALREADY_EXISTS = 'ALREADY_EXISTS'

    help = 'Creates a new client and optionally a client environment.'

    def add_arguments(self, parser):
        parser.add_argument('client_name', type=str, help='Name of the client')
        parser.add_argument('contact_name', type=str, help='Contact name for the client')
        parser.add_argument('contact_email', type=str, help='Contact email for the client')
        parser.add_argument('contact_url', type=str, help='Contact website for the client')

        # Named (optional) arguments
        parser.add_argument(
            '--env_type',
            type=str,
            help='Environment type (e.g. dev, stage, prod)',
        )
        # Named (optional) arguments
        parser.add_argument(
            '--env_redirect_url',
            type=str,
            help='Environment redirect url (where the user goes after auth)',
        )
        # Named (optional) arguments
        parser.add_argument(
            '--env_allowed_hostnames',
            type=str,
            help='Allowed hostnames (separated by commas, spaces are trimmed)',
        )

    def handle(self, *args, **options):
        client_name = options.get('client_name')
        contact_name = options.get('contact_name')
        contact_email = options.get('contact_email')
        contact_url = options.get('contact_url')
        env = options.get('env_type')
        env_redirect_url = options.get('env_redirect_url')
        env_allowed_hostnames = options.get('env_allowed_hostnames')
        make_env = [env, env_redirect_url, env_allowed_hostnames]
        verbosity = options.get('verbosity', 1)

        client_contact_result = create_client_contact.Command.ReturnCodes.ERROR
        client_env_result = create_client_environment.Command.ReturnCodes.ERROR

        if any(make_env) and not all(make_env):
            if verbosity > 0:
                self.stdout.write(self.style.ERROR('A client environment requires all env_* options to be filled'))
            return

        make_env = all(make_env)

        try:
            client = models.Client.objects.get(name=client_name)
        except models.Client.DoesNotExist:
            client = None

        if client:
            if verbosity > 0:
                self.stdout.write(self.style.ERROR(f'A client with the name {client_name} already exists'))
            return

        client = models.Client.objects.create(name=client_name)

        client_contact_result = management.call_command(
            'create_client_contact', client.uuid, contact_name, contact_email, contact_url, verbosity=0
        )

        if make_env:
            client_env_result = management.call_command(
                'create_client_environment', client.uuid, env, env_redirect_url, env_allowed_hostnames, verbosity=0
            )

        if client and verbosity > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Your client was successfully created with the uuid of {client.uuid}')
            )

        if all([client, client_contact_result == 0, client_env_result == 0]) and verbosity > 0:
            self.stdout.write(self.style.SUCCESS('Your Client Details:'))
            self.stdout.write(self.style.SUCCESS(f'* Client ID: {client.uuid}'))
            self.stdout.write(self.style.SUCCESS(f'* Client Secret: {client.clientenvironment_set.first().auth_token}'))

        return self.ReturnCodes.OK.value
