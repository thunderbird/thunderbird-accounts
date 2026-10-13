from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from thunderbird_accounts.mail.exceptions import JMapOriginMismatchError
from thunderbird_accounts.mail.tiny_jmap_client import TinyJMAPClient


def _response(status_code=200, data=None, location=None):
    response = MagicMock()
    response.status_code = status_code
    response.is_redirect = location is not None
    response.headers = {'Location': location} if location else {}
    response.json.return_value = data
    return response


class TinyJMAPClientTransportTestCase(SimpleTestCase):
    def setUp(self):
        self.client = TinyJMAPClient('https://mail.example.org', 'user@example.org', 'user-token', timeout=7)

    @patch('thunderbird_accounts.mail.tiny_jmap_client.requests.get')
    def test_session_on_another_origin_is_rejected_every_time(self, get_mock: MagicMock):
        get_mock.return_value = _response(data={'apiUrl': 'https://attacker.example/jmap/'})

        for _ in range(2):
            with self.assertRaises(JMapOriginMismatchError):
                self.client.get_session()
        self.assertIsNone(self.client.session)
        self.assertEqual(get_mock.call_args.kwargs['timeout'], 7)

    @patch('thunderbird_accounts.mail.tiny_jmap_client.requests.post')
    def test_api_calls_do_not_follow_redirects(self, post_mock: MagicMock):
        post_mock.return_value = _response(status_code=307, location='https://elsewhere.example/jmap/')
        self.client.api_url = 'https://mail.example.org/jmap/'

        with self.assertRaisesRegex(RuntimeError, '307 redirect'):
            self.client.make_jmap_call({'using': [], 'methodCalls': []})

        self.assertIs(post_mock.call_args.kwargs['allow_redirects'], False)
        self.assertEqual(post_mock.call_args.kwargs['timeout'], 7)
