from django.core.management.base import BaseCommand
from thunderbird_accounts.mail.client import MailClient


class Command(BaseCommand):
    help = 'Creates and saves a stalwart api key to .env'

    def handle(self, *args, **options):
        with open('.env') as fh:
            if 'STALWART_API_KEY=api_' in fh.read():
                raise RuntimeError('Stalwart API key already exists in your env!')

        mail = MailClient()
        api_key = mail.make_api_key('admin', 'accounts')

        env = None
        with open('.env') as fh:
            env = fh.read()
            env = env.replace('STALWART_API_KEY=', f'STALWART_API_KEY={api_key}')

        with open('.env', 'w') as fh:
            fh.write(env)
