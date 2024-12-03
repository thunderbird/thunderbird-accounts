from urllib.parse import urljoin

from django.conf import settings


def get_absolute_url(path: str) -> str:
    """Prepend a path with the correct public facing url, if the path is already an absolute url it returns itself unmodified."""
    if path.startswith('http') or path.startswith('https'):
        return path

    return urljoin(settings.PUBLIC_BASE_URL, path)
