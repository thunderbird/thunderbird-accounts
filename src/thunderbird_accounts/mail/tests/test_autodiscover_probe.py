import socket
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from thunderbird_accounts.mail.autodiscover_probe import (
    AUTODISCOVER_PROBE_PATH,
    AUTODISCOVER_PROBE_TIMEOUT,
    _safe_autodiscover_request_targets,
    exchange_autodiscover_endpoint_exists,
)


def _response(status_code: int, *, body: bytes = b'', headers: dict | None = None, is_redirect: bool = False):
    """Build a minimal requests-like response for probe tests."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.is_redirect = is_redirect
    response.raw.read.return_value = body
    return response


class TestExchangeAutodiscoverEndpointExists(SimpleTestCase):
    def _mock_getaddrinfo(self, ip_address='93.184.216.34'):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip_address, 443))]

    def test_posts_autodiscover_xml_to_vetted_ip_and_accepts_unauthorized(self):
        with (
            patch('thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo') as mock_getaddrinfo,
            patch('thunderbird_accounts.mail.autodiscover_probe.requests.Session') as mock_session_cls,
        ):
            mock_getaddrinfo.return_value = self._mock_getaddrinfo()
            mock_session = mock_session_cls.return_value
            mock_session.post.return_value = _response(401)

            exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertTrue(exists)
        self.assertFalse(mock_session.trust_env)
        self.assertEqual(mock_session.mount.call_args.args[0], 'https://')
        mock_getaddrinfo.assert_called_once_with('autodiscover.example.com', 443, type=socket.SOCK_STREAM)
        mock_session.post.assert_called_once()
        post_kwargs = mock_session.post.call_args.kwargs
        self.assertEqual(post_kwargs['headers']['Content-Type'], 'text/xml; charset=utf-8')
        self.assertEqual(post_kwargs['headers']['Host'], 'autodiscover.example.com')
        self.assertEqual(post_kwargs['timeout'], AUTODISCOVER_PROBE_TIMEOUT)
        self.assertFalse(post_kwargs['allow_redirects'])
        self.assertIn(b'<EMailAddress>autodiscover-probe@example.com</EMailAddress>', post_kwargs['data'])
        self.assertIn(b'<AcceptableResponseSchema>', post_kwargs['data'])
        self.assertEqual(mock_session.post.call_args.args[0], f'https://93.184.216.34:443{AUTODISCOVER_PROBE_PATH}')

    def test_does_not_accept_generic_success_response(self):
        def getaddrinfo(host, port, type):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))]

        with (
            patch('thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo', side_effect=getaddrinfo),
            patch('thunderbird_accounts.mail.autodiscover_probe.requests.Session') as mock_session_cls,
        ):
            mock_session = mock_session_cls.return_value
            mock_session.post.return_value = _response(200, body=b'<html>Wildcard site</html>')

            exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertFalse(exists)
        self.assertEqual(mock_session.post.call_count, 2)

    def test_accepts_success_response_that_mentions_autodiscover(self):
        with (
            patch(
                'thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo',
                return_value=self._mock_getaddrinfo(),
            ),
            patch('thunderbird_accounts.mail.autodiscover_probe.requests.Session') as mock_session_cls,
        ):
            mock_session = mock_session_cls.return_value
            mock_session.post.return_value = _response(200, body=b'<Autodiscover><Response /></Autodiscover>')

            exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertTrue(exists)
        mock_session.post.assert_called_once()

    def test_follows_redirects_with_post_body(self):
        def getaddrinfo(host, port, type):
            ip_address = '93.184.216.35' if host == 'outlook.example.net' else '93.184.216.34'
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip_address, port))]

        with (
            patch('thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo', side_effect=getaddrinfo),
            patch('thunderbird_accounts.mail.autodiscover_probe.requests.Session') as mock_session_cls,
        ):
            mock_session = mock_session_cls.return_value
            mock_session.post.side_effect = [
                _response(
                    302,
                    headers={'Location': 'https://outlook.example.net/autodiscover/autodiscover.xml'},
                    is_redirect=True,
                ),
                _response(401),
            ]

            exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertTrue(exists)
        self.assertEqual(
            [call_args.args[0] for call_args in mock_session.post.call_args_list],
            [
                f'https://93.184.216.34:443{AUTODISCOVER_PROBE_PATH}',
                f'https://93.184.216.35:443{AUTODISCOVER_PROBE_PATH}',
            ],
        )
        self.assertEqual(
            [call_args.kwargs['headers']['Host'] for call_args in mock_session.post.call_args_list],
            ['autodiscover.example.com', 'outlook.example.net'],
        )
        self.assertEqual(
            mock_session.post.call_args_list[0].kwargs['data'], mock_session.post.call_args_list[1].kwargs['data']
        )

    def test_does_not_request_unsafe_urls(self):
        with (
            patch(
                'thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo',
                return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))],
            ),
            patch('thunderbird_accounts.mail.autodiscover_probe.requests.Session') as mock_session_cls,
        ):
            mock_session = mock_session_cls.return_value

            exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertFalse(exists)
        mock_session.post.assert_not_called()

    @patch('thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo')
    def test_raw_ip_url_is_unsafe(self, mock_getaddrinfo):
        self.assertEqual(_safe_autodiscover_request_targets('https://93.184.216.34/autodiscover/autodiscover.xml'), [])
        mock_getaddrinfo.assert_not_called()

    @patch('thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo')
    def test_rejects_mixed_public_and_private_dns_answers(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443)),
        ]

        targets = _safe_autodiscover_request_targets('https://autodiscover.example.com/autodiscover/autodiscover.xml')

        self.assertEqual(targets, [])
