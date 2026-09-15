from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from thunderbird_accounts.authentication.exceptions import RoleMappingError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.subscription.models import Subscription

ROLE = settings.KEYCLOAK_MAIL_ACCESS_ROLE
ROLE_REPRESENTATION = {'id': 'role-uuid', 'name': ROLE}
SCOPE = settings.KEYCLOAK_PRE_PROVISIONING_SCOPE


@override_settings(OIDC_RP_CLIENT_ID='tb-accounts')
@patch('thunderbird_accounts.mail.management.commands.backfill_mail_access_role.KeycloakClient')
class BackfillMailAccessRoleCommandTests(TestCase):
    """Pins who is granted, who is reported as locked out, and the exemption check."""

    def setUp(self):
        domain = settings.PRIMARY_EMAIL_DOMAIN
        self.provisioned = User.objects.create(username=f'provisioned@{domain}', oidc_id='oidc-provisioned')
        Account.objects.create(name=self.provisioned.username, user=self.provisioned, stalwart_id='1')
        self.already_granted = User.objects.create(username=f'granted@{domain}', oidc_id='oidc-granted')
        Account.objects.create(name=self.already_granted.username, user=self.already_granted, stalwart_id='2')
        # Paying, but never linked to a Stalwart principal (with and without a local Account row).
        self.unlinked = User.objects.create(username=f'unlinked@{domain}', oidc_id='oidc-unlinked')
        Account.objects.create(name=self.unlinked.username, user=self.unlinked)
        Subscription.objects.create(user=self.unlinked, status=Subscription.StatusValues.ACTIVE)
        self.no_account = User.objects.create(username=f'noaccount@{domain}', oidc_id='oidc-noaccount')
        Subscription.objects.create(user=self.no_account, status=Subscription.StatusValues.ACTIVE)
        # Not reported: cancelled without a mailbox, and linked without a Keycloak identity.
        cancelled = User.objects.create(username=f'cancelled@{domain}', oidc_id='oidc-cancelled')
        Subscription.objects.create(user=cancelled, status=Subscription.StatusValues.CANCELED)
        legacy = User.objects.create(username=f'legacy@{domain}')
        Account.objects.create(name=legacy.username, user=legacy, stalwart_id='3')

    def _run(self, *args):
        out, err = StringIO(), StringIO()
        call_command('backfill_mail_access_role', *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def _configure(self, keycloak_cls, granted=(), accounts_scopes=(SCOPE, 'profile')):
        keycloak = keycloak_cls.return_value
        keycloak.get_realm_role.return_value = ROLE_REPRESENTATION
        keycloak.get_client_default_scope_names.return_value = list(accounts_scopes)
        keycloak.get_realm_role_member_ids.return_value = set(granted)
        return keycloak

    def test_grants_linked_users_without_the_role(self, keycloak_cls):
        keycloak = self._configure(keycloak_cls, granted=('oidc-granted',))

        out, err = self._run()

        keycloak.grant_realm_role.assert_called_once_with('oidc-provisioned', ROLE, role=ROLE_REPRESENTATION)
        keycloak.get_client_default_scope_names.assert_called_once_with('tb-accounts')
        self.assertIn(f'granted {ROLE}: {self.provisioned.username}', out)
        self.assertIn(f'1 granted, 1 already had {ROLE}, 0 failed, 2 active subscribers', out)
        self.assertEqual(err, '')

    def test_dry_run_reads_but_never_grants(self, keycloak_cls):
        keycloak = self._configure(keycloak_cls)

        out, _ = self._run('--dry-run')

        keycloak.grant_realm_role.assert_not_called()
        self.assertIn(f'would grant {ROLE}: {self.provisioned.username}', out)
        for user in (self.unlinked, self.no_account):
            self.assertIn(f'active subscription without a linked mailbox: {user.username}', out)
        self.assertNotIn('cancelled@', out)
        self.assertNotIn('legacy@', out)
        self.assertIn('dry run: 2 granted, 0 already had', out)

    def test_failed_grant_fails_the_command(self, keycloak_cls):
        keycloak = self._configure(keycloak_cls)
        keycloak.grant_realm_role.side_effect = [RoleMappingError(error='boom', role_name=ROLE), None]

        with self.assertRaises(CommandError) as ctx:
            self._run()

        self.assertIn('1 role grant(s) failed', str(ctx.exception))
        self.assertEqual(keycloak.grant_realm_role.call_count, 2)

    def test_missing_accounts_exemption_blocks_the_real_run(self, keycloak_cls):
        keycloak = self._configure(keycloak_cls, accounts_scopes=('profile',))

        with self.assertRaises(CommandError) as ctx:
            self._run()
        self.assertIn('lock users out of accounts', str(ctx.exception))
        keycloak.grant_realm_role.assert_not_called()

        keycloak.get_realm_role.side_effect = RoleMappingError(error='Error<404>', role_name=ROLE)
        out, err = self._run('--dry-run')
        self.assertIn(f'lacks the {SCOPE} default scope', err)
        self.assertIn('Error<404>', err)
        self.assertIn(f'would grant {ROLE}: {self.provisioned.username}', out)
