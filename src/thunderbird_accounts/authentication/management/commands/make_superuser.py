from django.core.management.base import BaseCommand, CommandError
from thunderbird_accounts.authentication.models import User


class Command(BaseCommand):
    help = 'For each email address provided, make user a superuser'

    def add_arguments(self, parser):
        parser.add_argument('emails', nargs='+', type=str)

    def handle(self, *args, **options):
        emails = options['emails']
        for email in emails:
            u = None
            try:
                u = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f'User {email} does not exist')
            if u:
                u.is_superuser = True
                u.is_staff = True
                u.save()

            self.stdout.write(self.style.SUCCESS(f'User {email} is now a superuser'))
