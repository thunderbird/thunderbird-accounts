"""Grant the Keycloak mail-access role to every user with a linked Stalwart mailbox.

Run before the Keycloak gate is enabled so existing users keep signing in to their mail
clients. Also lists active subscribers without a linked mailbox, whom the gate will deny.

Usage:

.. code-block:: shell

    python manage.py backfill_mail_access_role --dry-run
    python manage.py backfill_mail_access_role
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import RoleMappingError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.subscription.models import Subscription


def provisioned_users():
    """Users with a Keycloak identity and a mail account linked to a Stalwart principal."""
    return (
        User.objects.filter(oidc_id__isnull=False, account__stalwart_id__isnull=False)
        .exclude(oidc_id='')
        .exclude(account__stalwart_id='')
        .distinct()
        .order_by('username')
    )


def unprovisioned_subscribers():
    """Active subscribers without a linked mailbox."""
    return (
        User.objects.filter(subscription__status=Subscription.StatusValues.ACTIVE)
        .exclude(pk__in=provisioned_users().values('pk'))
        .distinct()
        .order_by('username')
    )


class Command(BaseCommand):
    help = 'Grant the Keycloak mail-access role to every user with a linked Stalwart mailbox.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report without modifying Keycloak.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        role_name = settings.KEYCLOAK_MAIL_ACCESS_ROLE
        scope_name = settings.KEYCLOAK_PRE_PROVISIONING_SCOPE
        keycloak = KeycloakClient()

        # Without this exemption the gate would also deny accounts sign-in to every user lacking the role.
        default_scopes = keycloak.get_client_default_scope_names(settings.OIDC_RP_CLIENT_ID)
        if default_scopes is None or scope_name not in default_scopes:
            problem = f'client {settings.OIDC_RP_CLIENT_ID!r} lacks the {scope_name} default scope'
            if not dry_run:
                raise CommandError(f'{problem}; enabling the gate would lock users out of accounts.')
            self.stderr.write(f'gate prerequisite missing: {problem}')

        role = None
        member_ids: set[str] = set()
        try:
            role = keycloak.get_realm_role(role_name)
            member_ids = keycloak.get_realm_role_member_ids(role_name)
        except RoleMappingError as ex:
            if not dry_run:
                raise CommandError(str(ex))
            self.stderr.write(f'gate prerequisite missing: {ex}')

        granted = already_granted = failed = 0
        for user in provisioned_users().iterator():
            if user.oidc_id in member_ids:
                already_granted += 1
                continue
            try:
                if not dry_run:
                    keycloak.grant_realm_role(user.oidc_id, role_name, role=role)
                granted += 1
                self.stdout.write(f'{"would grant" if dry_run else "granted"} {role_name}: {user.username}')
            except RoleMappingError as ex:
                failed += 1
                self.stderr.write(f'failed {user.username}: {ex}')

        locked_out = list(unprovisioned_subscribers())
        for user in locked_out:
            self.stdout.write(f'active subscription without a linked mailbox: {user.username} ({user.uuid})')

        self.stdout.write(
            f'{"dry run: " if dry_run else ""}{granted} granted, {already_granted} already had {role_name}, '
            f'{failed} failed, {len(locked_out)} active subscribers without a mailbox.'
        )
        if failed:
            raise CommandError(f'{failed} role grant(s) failed.')
