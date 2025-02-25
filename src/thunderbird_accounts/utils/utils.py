import json
from urllib.parse import urljoin

from django.conf import settings


def get_absolute_url(path: str) -> str:
    """Prepend a path with the correct public facing url, if the path is already an absolute url it returns itself unmodified."""
    if path.startswith('http') or path.startswith('https'):
        return path

    return urljoin(settings.PUBLIC_BASE_URL, path)


class JsonSerializer:
    """A json-based serializer for our shared redis cache."""

    def __init__(self, protocol=None):
        # Not used, but we'll store it just in case
        self.protocol = protocol

    def dumps(self, obj):
        print("Transforming ->", obj)
        print("To ->",json.dumps(obj))
        return json.dumps(obj)

    def loads(self, obj):
        return json.loads(obj)
