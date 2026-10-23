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


class UserDeactivatedAtTestCase(TestCase):
    def _make_user(self, **kwargs) -> User:
        return User.objects.create(username='person@example.org', email='recovery@example.com', **kwargs)

    def test_active_user_has_no_timestamp(self):
        self.assertIsNone(self._make_user().deactivated_at)

    def test_user_created_inactive_is_stamped(self):
        self.assertIsNotNone(self._make_user(is_active=False).deactivated_at)

    def test_deactivation_stamps_and_reactivation_clears(self):
        user = self._make_user()

        user.is_active = False
        user.save()
        user.refresh_from_db()
        self.assertIsNotNone(user.deactivated_at)

        user.is_active = True
        user.save()
        user.refresh_from_db()
        self.assertIsNone(user.deactivated_at)

    def test_unrelated_saves_keep_the_timestamp(self):
        user = self._make_user(is_active=False)
        stamped_at = user.deactivated_at

        user.display_name = 'Someone'
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.deactivated_at, stamped_at)

    def test_timestamp_is_persisted_when_saving_with_update_fields(self):
        user = self._make_user()

        user.is_active = False
        user.save(update_fields=['is_active'])
        user.refresh_from_db()

        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deactivated_at)
