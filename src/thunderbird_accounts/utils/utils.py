import json
from urllib.parse import urljoin
from ua_parser import parse_user_agent, parse_os

from django.conf import settings


def get_absolute_url(path: str) -> str:
    """Prepend a path with the correct public facing url,
    if the path is already an absolute url it returns itself unmodified."""
    if path.startswith('http') or path.startswith('https'):
        return path

    return urljoin(settings.PUBLIC_BASE_URL, path)


class JsonSerializer:
    """A json-based serializer for our shared redis cache."""

    def __init__(self, protocol=None):
        # Not used, but we'll store it just in case
        self.protocol = protocol

    def dumps(self, obj):
        return json.dumps(obj)

    def loads(self, obj):
        return json.loads(obj)


def parse_user_agent_info(user_agent_string: str) -> tuple[str, str]:
    """Parse user agent string and return separate browser and OS information."""

    # Extract browser information
    browser_info = parse_user_agent(user_agent_string)
    browser_string = f"{browser_info.family}"
    if browser_info.major:
        browser_string += f" {browser_info.major}"
        if browser_info.minor:
            browser_string += f".{browser_info.minor}"
            if browser_info.patch:
                browser_string += f".{browser_info.patch}"

    # Extract OS information
    os_info = parse_os(user_agent_string)
    os_string = f"{os_info.family}"
    if os_info.major:
        os_string += f" {os_info.major}"
        if os_info.minor:
            os_string += f".{os_info.minor}"
            if os_info.patch:
                os_string += f".{os_info.patch}"

    return browser_string, os_string
