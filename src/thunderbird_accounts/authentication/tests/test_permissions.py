from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.permissions import user_owns_email
from thunderbird_accounts.mail.models import Account, Email


class UserOwnsEmailTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='owner@example.org',
            email='owner-login@example.org',
            recovery_email='owner-recovery@example.net',
            oidc_id='owner-1',
        )
        account = Account.objects.create(name=self.user.username, user=self.user)
        Email.objects.create(address=self.user.username, type=Email.EmailType.PRIMARY, account=account)
        Email.objects.create(address='owner-alias@example.org', type=Email.EmailType.ALIAS, account=account)

        self.other = User.objects.create(username='other@example.org', email='other@example.org', oidc_id='other-1')
        other_account = Account.objects.create(name=self.other.username, user=self.other)
        Email.objects.create(address='other-alias@example.org', type=Email.EmailType.ALIAS, account=other_account)

    def test_matches_every_address_on_the_users_record(self):
        for address in (
            'owner@example.org',
            'owner-login@example.org',
            'owner-recovery@example.net',
            'owner-alias@example.org',
        ):
            with self.subTest(address=address):
                self.assertTrue(user_owns_email(self.user, address))

    def test_match_is_case_insensitive_and_ignores_surrounding_whitespace(self):
        self.assertTrue(user_owns_email(self.user, '  Owner-Alias@Example.ORG '))

    def test_does_not_match_other_users_or_unknown_addresses(self):
        for address in ('other@example.org', 'other-alias@example.org', 'nobody@example.org'):
            with self.subTest(address=address):
                self.assertFalse(user_owns_email(self.user, address))

    def test_anonymous_user_or_empty_email_never_matches(self):
        self.assertFalse(user_owns_email(AnonymousUser(), 'owner@example.org'))
        self.assertFalse(user_owns_email(None, 'owner@example.org'))
        self.assertFalse(user_owns_email(self.user, ''))
        self.assertFalse(user_owns_email(self.user, None))
