from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.exceptions import EmailNotValidError
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.mail.types.jmap import Invocation, JMapResponse
from thunderbird_accounts.mail.utils import fix_archives_folder, validate_email


class FixArchivesFolderClientSelectionTestCase(TestCase):
    @override_settings(
        STALWART_ADMIN_API_USE_JMAP=True,
        STALWART_BASE_JMAP_URL='http://stalwart_legacy:8081',
        STALWART_JMAP_API_URL='http://stalwart_new:8080',
    )
    @patch('thunderbird_accounts.mail.tiny_jmap_client.TinyJMAPClient')
    @patch('thunderbird_accounts.mail.clients.mail_client_jmap.JMAPClient')
    def test_jmap_flag_uses_v016_user_endpoint(self, jmap_client_mock: MagicMock, tiny_jmap_client_mock: MagicMock):
        account = MagicMock(spec=Account)
        account.name = 'user@example.org'
        access_token = 'oidc-access-token'

        legacy_client = tiny_jmap_client_mock.return_value
        legacy_client.get_account_id.return_value = 'legacy-account'
        legacy_client.make_jmap_call.side_effect = [
            {'methodResponses': [['Mailbox/query', {'ids': []}, '0']]},
            {'methodResponses': [['Mailbox/set', {'created': {'temp-id': {'id': 'archive-id'}}}, '0']]},
        ]

        user_client = jmap_client_mock.return_value
        user_client.get_account_id.return_value = 'user-account'
        query_response = JMapResponse(
            method_responses=[Invocation(name='Mailbox/query', arguments={'ids': []}, method_call_id='0')],
            session_state='state-1',
        )
        set_response = JMapResponse(
            method_responses=[
                Invocation(
                    name='Mailbox/set',
                    arguments={'created': {'temp-id': {'id': 'archive-id'}}},
                    method_call_id='0',
                )
            ],
            session_state='state-2',
        )
        user_client.request.side_effect = [query_response, set_response]

        with patch('thunderbird_accounts.mail.utils.uuid.uuid4', return_value='temp-id'):
            self.assertTrue(fix_archives_folder(access_token, account))
        jmap_client_mock.assert_called_once()
        self.assertEqual(
            jmap_client_mock.call_args.args[:3],
            ('http://stalwart_new:8080', account.name, access_token),
        )
        self.assertEqual(
            [call.args[0].method_calls[0].name for call in user_client.request.call_args_list],
            ['Mailbox/query', 'Mailbox/set'],
        )
        tiny_jmap_client_mock.assert_not_called()


class ValidateEmailTestCase(TestCase):
    """Tests for validate_email, focused on the local-part length check.

    USERNAME_MIN_LENGTH = 3  →  local parts shorter than 3 chars are rejected
    USERNAME_MAX_LENGTH = 150 →  local parts longer than 150 chars are rejected
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

    # ------------------------------------------------------------------
    # min_length override
    # ------------------------------------------------------------------

    def test_min_length_override_allows_short_local_part(self):
        """Callers can lower the minimum below USERNAME_MIN_LENGTH."""
        self.assertTrue(validate_email(self._email('a'), min_length=1))

    def test_min_length_override_still_rejects_below_override(self):
        """The overridden minimum is still enforced."""
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(''), min_length=1)
