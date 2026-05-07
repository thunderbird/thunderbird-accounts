from django.core.exceptions import ValidationError
from django.test import TestCase

from thunderbird_accounts.authentication.models import User


class UserUsernameValidatorTestCase(TestCase):
    """Verify that the MinLengthValidator is wired to User.username.

    max_length is enforced at the DB column level by Django's CharField.
    min_length is enforced only via validators, so it is important to confirm
    the validator is actually attached to the field.
    """

    # Fields not relevant to username validation that are nullable without
    # blank=True — exclude them so full_clean() only validates what we care about.
    _EXCLUDE = ['password', 'oidc_id', 'recovery_email', 'last_used_email', 'display_name', 'avatar_url']

    def _make_user(self, username: str) -> User:
        return User(username=username, email='recovery@example.com')

    def test_username_at_min_length_passes(self):
        """A username of exactly USERNAME_MIN_LENGTH (3) characters is valid."""
        user = self._make_user('a' * User.USERNAME_MIN_LENGTH)
        # full_clean() runs all field validators; should not raise
        user.full_clean(exclude=self._EXCLUDE)

    def test_username_below_min_length_raises(self):
        """A username shorter than USERNAME_MIN_LENGTH (3) fails validation."""
        user = self._make_user('a' * (User.USERNAME_MIN_LENGTH - 1))
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean(exclude=self._EXCLUDE)
        self.assertIn('username', ctx.exception.message_dict)

    def test_username_at_max_length_passes(self):
        """A username of exactly USERNAME_MAX_LENGTH (150) characters is valid."""
        user = self._make_user('a' * User.USERNAME_MAX_LENGTH)
        user.full_clean(exclude=self._EXCLUDE)

    def test_username_above_max_length_raises(self):
        """A username longer than USERNAME_MAX_LENGTH (150) fails validation."""
        user = self._make_user('a' * (User.USERNAME_MAX_LENGTH + 1))
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean(exclude=self._EXCLUDE)
        self.assertIn('username', ctx.exception.message_dict)
