"""
ASGI config for thunderbird_accounts project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.conf import settings
from django.core.asgi import get_asgi_application

from servestatic import ServeStaticASGI

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thunderbird_accounts.settings')


def immutable_file_test(path, url):
    # Match vite (rollup)-generated hashes, à la, `some_file-CSliV9zW.js`
    import re
    return re.match(r'^.+[.-][0-9a-zA-Z_-]{8,12}\..+$', url)


application = get_asgi_application()
if not settings.DEBUG:
    application = ServeStaticASGI(
        application, root=settings.STATIC_ROOT, prefix='static', immutable_file_test=immutable_file_test
    )
