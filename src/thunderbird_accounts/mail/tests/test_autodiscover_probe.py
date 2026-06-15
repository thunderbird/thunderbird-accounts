from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from thunderbird_accounts.mail.autodiscover_probe import (
    AUTODISCOVER_PROBE_PATH,
    AUTODISCOVER_PROBE_TIMEOUT,
    _is_safe_autodiscover_url,
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
    @patch('thunderbird_accounts.mail.autodiscover_probe._is_safe_autodiscover_url', return_value=True)
    @patch('thunderbird_accounts.mail.autodiscover_probe.requests.post')
    def test_posts_autodiscover_xml_and_accepts_unauthorized(self, mock_post, mock_is_safe):
        mock_post.return_value = _response(401)

        exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertTrue(exists)
        mock_is_safe.assert_called_once_with(f'https://autodiscover.example.com{AUTODISCOVER_PROBE_PATH}')
        mock_post.assert_called_once()
        post_kwargs = mock_post.call_args.kwargs
        self.assertEqual(post_kwargs['headers']['Content-Type'], 'text/xml; charset=utf-8')
        self.assertEqual(post_kwargs['timeout'], AUTODISCOVER_PROBE_TIMEOUT)
        self.assertFalse(post_kwargs['allow_redirects'])
        self.assertIn(b'<EMailAddress>autodiscover-probe@example.com</EMailAddress>', post_kwargs['data'])
        self.assertIn(b'<AcceptableResponseSchema>', post_kwargs['data'])
        self.assertEqual(mock_post.call_args.args[0], f'https://autodiscover.example.com{AUTODISCOVER_PROBE_PATH}')

    @patch('thunderbird_accounts.mail.autodiscover_probe._is_safe_autodiscover_url', return_value=True)
    @patch('thunderbird_accounts.mail.autodiscover_probe.requests.post')
    def test_does_not_accept_generic_success_response(self, mock_post, mock_is_safe):
        mock_post.return_value = _response(200, body=b'<html>Wildcard site</html>')

        exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertFalse(exists)
        self.assertEqual(mock_is_safe.call_count, 2)
        self.assertEqual(mock_post.call_count, 2)

    @patch('thunderbird_accounts.mail.autodiscover_probe._is_safe_autodiscover_url', return_value=True)
    @patch('thunderbird_accounts.mail.autodiscover_probe.requests.post')
    def test_accepts_success_response_that_mentions_autodiscover(self, mock_post, mock_is_safe):
        mock_post.return_value = _response(200, body=b'<Autodiscover><Response /></Autodiscover>')

        exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertTrue(exists)
        mock_is_safe.assert_called_once()
        mock_post.assert_called_once()

    @patch('thunderbird_accounts.mail.autodiscover_probe._is_safe_autodiscover_url', return_value=True)
    @patch('thunderbird_accounts.mail.autodiscover_probe.requests.post')
    def test_follows_redirects_with_post_body(self, mock_post, mock_is_safe):
        mock_post.side_effect = [
            _response(
                302,
                headers={'Location': 'https://outlook.example.net/autodiscover/autodiscover.xml'},
                is_redirect=True,
            ),
            _response(401),
        ]

        exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertTrue(exists)
        self.assertEqual(mock_is_safe.call_count, 2)
        self.assertEqual(
            [call_args.args[0] for call_args in mock_post.call_args_list],
            [
                f'https://autodiscover.example.com{AUTODISCOVER_PROBE_PATH}',
                f'https://outlook.example.net{AUTODISCOVER_PROBE_PATH}',
            ],
        )
        self.assertEqual(mock_post.call_args_list[0].kwargs['data'], mock_post.call_args_list[1].kwargs['data'])

    @patch('thunderbird_accounts.mail.autodiscover_probe._is_safe_autodiscover_url', return_value=False)
    @patch('thunderbird_accounts.mail.autodiscover_probe.requests.post')
    def test_does_not_request_unsafe_urls(self, mock_post, mock_is_safe):
        exists = exchange_autodiscover_endpoint_exists('autodiscover.example.com', 'example.com')

        self.assertFalse(exists)
        self.assertEqual(mock_is_safe.call_count, 2)
        mock_post.assert_not_called()

    @patch('thunderbird_accounts.mail.autodiscover_probe.socket.getaddrinfo')
    def test_raw_ip_url_is_unsafe(self, mock_getaddrinfo):
        self.assertFalse(_is_safe_autodiscover_url('https://203.0.113.10/autodiscover/autodiscover.xml'))
        mock_getaddrinfo.assert_not_called()
