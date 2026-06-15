"""
Code for probing if a custom domain's autodiscover subdomain belongs to an Exchange server.

If so, that's a conflict to flag to the user.
"""
import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import requests
AUTODISCOVER_PROBE_PATH = '/autodiscover/autodiscover.xml'
AUTODISCOVER_PROBE_MAX_REDIRECTS = 3
AUTODISCOVER_PROBE_MAX_BYTES = 65536
# Short time-outs should be sufficient for legit servers and is better UX.
AUTODISCOVER_PROBE_TIMEOUT = (0.75, 1.0)
AUTODISCOVER_PROBE_HEADERS = {
    # outlook.com needs this exact string, with space and lower case "utf".
    'Content-Type': 'text/xml; charset=utf-8',
}
AUTODISCOVER_EXCHANGE_HEADER_NAMES = {
    'x-beserver',
    'x-calculatedbetarget',
    'x-diaginfo',
    'x-feserver',
    'x-msdiagnostics',
    'x-owa-version',
}
AUTODISCOVER_EXCHANGE_TERMS = ('autodiscover', 'exchange', 'office365', 'outlook')


def _autodiscover_probe_body(domain_name: str) -> str:
    """Build the minimal Exchange Autodiscover XML request body."""
    email_address = f'autodiscover-probe@{domain_name}'
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Autodiscover xmlns="http://schemas.microsoft.com/exchange/autodiscover/outlook/requestschema/2006">
  <Request>
    <EMailAddress>{email_address}</EMailAddress>
    <AcceptableResponseSchema>http://schemas.microsoft.com/exchange/autodiscover/outlook/responseschema/2006a</AcceptableResponseSchema>
  </Request>
</Autodiscover>'''


def _is_safe_autodiscover_url(url: str) -> bool:
    """
    Because we are making HTTP + DNS requests to user-controlled domain,
    Make various security checks for the actual HTTP request.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or parsed.port not in {None, 80, 443}:
            return False
        if not parsed.hostname or parsed.username or parsed.password:
            return False
        try:
            ipaddress.ip_address(parsed.hostname)
            return False
        except ValueError:
            pass

        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        # SSRF check: resolve customer-controlled hostnames before requesting them so they cannot
        # send backend HTTP traffic to private, loopback, link-local, or metadata addresses.
        for address_info in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM):
            address = ipaddress.ip_address(address_info[4][0])
            if not address.is_global:
                return False
    except (OSError, ValueError):
        return False

    return True


def _body_mentions_autodiscover(body: bytes) -> bool:
    return b'autodiscover' in body.lower()


def _has_exchange_autodiscover_evidence(response: requests.Response, body: bytes) -> bool:
    if _body_mentions_autodiscover(body):
        return True

    for name, value in response.headers.items():
        name = name.lower()
        value = value.lower()
        if name in AUTODISCOVER_EXCHANGE_HEADER_NAMES:
            return True
        if any(term in value for term in AUTODISCOVER_EXCHANGE_TERMS):
            return True
    return False


def _looks_like_exchange(response: requests.Response, body: bytes) -> bool:
    """Besides 200, Exchange might response to probe with some 4XX responses (but not 404!)"""
    if response.status_code == 401:
        return True
    if 200 <= response.status_code < 300:
        return _body_mentions_autodiscover(body)
    if response.status_code in {400, 403, 405}:
        return _has_exchange_autodiscover_evidence(response, body)
    return False


def exchange_autodiscover_endpoint_exists(hostname: str, domain_name: str) -> bool:
    """Probe a host for a functional Exchange Autodiscover endpoint."""
    body = _autodiscover_probe_body(domain_name).encode()

    for scheme in ('https', 'http'):
        url = f'{scheme}://{hostname}{AUTODISCOVER_PROBE_PATH}'
        for _ in range(AUTODISCOVER_PROBE_MAX_REDIRECTS + 1):
            if not _is_safe_autodiscover_url(url):
                break

            try:
                response = requests.post(
                    url,
                    data=body,
                    headers=AUTODISCOVER_PROBE_HEADERS,
                    timeout=AUTODISCOVER_PROBE_TIMEOUT,
                    allow_redirects=False,
                    stream=True,
                )
            except requests.RequestException as e:
                logging.debug(f'Autodiscover probe failed for {url}: {e}')
                break

            try:
                if response.is_redirect:
                    redirect_url = response.headers.get('Location')
                    if not redirect_url:
                        break
                    url = urljoin(url, redirect_url)
                    continue

                response_body = response.raw.read(AUTODISCOVER_PROBE_MAX_BYTES, decode_content=True)
                if _looks_like_exchange(response, response_body):
                    return True
                break
            finally:
                response.close()

    return False
