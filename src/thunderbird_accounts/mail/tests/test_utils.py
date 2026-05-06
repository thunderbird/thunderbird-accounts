from django.test import TestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.exceptions import EmailNotValidError
from thunderbird_accounts.mail.utils import validate_email


class ValidateEmailTestCase(TestCase):
    """Tests for validate_email, focused on the local-part length check.

    USERNAME_MIN_LENGTH = 3  →  local parts shorter than 3 chars are rejected
    USERNAME_MAX_LENGTH = 150 →  local parts of 150 chars or more are rejected
                                 (note: the guard uses >=, so 150 is invalid)
    """

    DOMAIN = 'example.com'

    def _email(self, local_part: str) -> str:
        return f'{local_part}@{self.DOMAIN}'

    # ------------------------------------------------------------------
    # Boundary: minimum length
    # ------------------------------------------------------------------

    def test_local_part_at_min_length_is_valid(self):
        """A local part of exactly USERNAME_MIN_LENGTH (3) characters is accepted."""
        local_part = 'a' * User.USERNAME_MIN_LENGTH
        self.assertTrue(validate_email(self._email(local_part)))

    def test_local_part_one_below_min_raises(self):
        """A local part of USERNAME_MIN_LENGTH - 1 (2) characters is rejected."""
        local_part = 'a' * (User.USERNAME_MIN_LENGTH - 1)
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(local_part))

    def test_local_part_single_char_raises(self):
        """A single-character local part is rejected."""
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email('a'))

    def test_empty_local_part_raises(self):
        """An empty local part (length 0) is rejected."""
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(''))

    # ------------------------------------------------------------------
    # Boundary: maximum length
    # ------------------------------------------------------------------

    def test_local_part_at_max_length_is_valid(self):
        """A local part of exactly USERNAME_MAX_LENGTH (150) characters is accepted."""
        local_part = 'a' * User.USERNAME_MAX_LENGTH
        self.assertTrue(validate_email(self._email(local_part)))

    def test_local_part_above_max_raises(self):
        """A local part longer than USERNAME_MAX_LENGTH (150) is rejected."""
        local_part = 'a' * (User.USERNAME_MAX_LENGTH + 1)
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(local_part))

    # ------------------------------------------------------------------
    # Format checks
    # ------------------------------------------------------------------

    def test_missing_at_sign_raises(self):
        """An email without '@' is rejected before the length check."""
        with self.assertRaises(EmailNotValidError):
            validate_email('notanemail')

    def test_invalid_email_format_raises(self):
        """A string with '@' but an otherwise invalid format is rejected."""
        with self.assertRaises(EmailNotValidError):
            validate_email('abc@')

    def test_valid_email_returns_true(self):
        """A well-formed email within length bounds returns True."""
        self.assertTrue(validate_email('validuser@example.com'))

    # ------------------------------------------------------------------
    # Custom error message
    # ------------------------------------------------------------------

    def test_custom_error_message_is_used(self):
        """The caller-supplied error_message is propagated in the exception."""
        custom_msg = 'Custom error for tests'
        local_part = 'a' * (User.USERNAME_MIN_LENGTH - 1)
        with self.assertRaises(EmailNotValidError) as ctx:
            validate_email(self._email(local_part), error_message=custom_msg)
        self.assertEqual(ctx.exception.error_message, custom_msg)
