from django.core import management
from django.core.management.base import BaseCommand
from thunderbird_accounts.client import models


class Command(BaseCommand):
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

        if any(make_env) and not all(make_env):
            self.stdout.write(self.style.ERROR('A client environment requires all env_* options to be filled'))
            return

        make_env = all(make_env)

        try:
            client = models.Client.objects.get(name=client_name)
        except models.Client.DoesNotExist:
            client = None

        if client:
            self.stdout.write(self.style.ERROR(f'A client with the name {client_name} already exists'))
            return

        client = models.Client.objects.create(name=client_name)

        management.call_command(
            'create_client_contact', client.uuid, contact_name, contact_email, contact_url
        )

        if make_env:
            management.call_command(
                'create_client_environment',
                client.uuid,
                env,
                env_redirect_url,
                env_allowed_hostnames,

            )
        self.stdout.write(self.style.SUCCESS(f'Successfully created client {client_name} with uuid of {client.uuid}'))
