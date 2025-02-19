"""
WSGI config for thunderbird_accounts project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.conf import settings
from django.core.wsgi import get_wsgi_application

from servestatic import ServeStatic

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thunderbird_accounts.settings')

application = get_wsgi_application()
application = ServeStatic(application, root=settings.STATIC_ROOT, prefix='static')
