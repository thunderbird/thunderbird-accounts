"""
Bootstrap an active Subscription for an e2e test account.
"""

from django.core.management.base import BaseCommand

from thunderbird_accounts.authentication.clients import KeycloakClient, RequestMethods
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.subscription.models import Subscription


class Command(BaseCommand):
    """
    Used for e2e tests that need to traverse routes the Vue router gates behind
    an active subscription (e.g. ``/manage-mfa``). Idempotent — safe to run more
    than once.

    Looks up the Keycloak user by username so the Django ``User`` row carries
    the matching ``oidc_id``; otherwise mozilla-django-oidc would create a
    duplicate user on first sign-in.

    Usage:

    .. code-block:: shell

        python manage.py create_active_subscription_for_e2e_test admin@example.org
    """

    help = 'Make a user a test account with an active subscription (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='User username (typically an email).')

    def handle(self, *args, **options):
        username = options['username']

        kc_users = (
            KeycloakClient()
            .request('users', RequestMethods.GET, params={'username': username, 'exact': 'true'})
            .json()
        )
        if not kc_users:
            self.stderr.write(self.style.ERROR(f'User {username} not found in Keycloak.'))
            return

        keycloak_user = kc_users[0]
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                'oidc_id': keycloak_user['id'],
                'email': keycloak_user.get('email', username),
                'is_test_account': True,
            },
        )

        if not user.subscription_set.filter(status=Subscription.StatusValues.ACTIVE).exists():
            Subscription.objects.create(
                user=user,
                status=Subscription.StatusValues.ACTIVE,
                paddle_id='sub_e2e_test',
                paddle_customer_id='ctm_e2e_test',
            )

        self.stdout.write(self.style.SUCCESS(f'{username} is now a test account with an active subscription.'))
