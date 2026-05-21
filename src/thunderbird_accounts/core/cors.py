from django.conf import settings
from django.urls import Resolver404, resolve

from corsheaders.signals import check_request_enabled


def cors_allow_zendesk_sidebar(sender, request, **kwargs):
    if not settings.ZENDESK_SUBDOMAIN:
        return False

    # In dev mode allow this for all urls, so that one can use localhost
    if not settings.IS_DEV and request.headers.get('origin') != f'https://{settings.ZENDESK_SUBDOMAIN}.zendesk.com':
        return False

    try:
        match = resolve(request.path_info)
    except Resolver404:
        return False

    return match.url_name == 'api_zendesk_sidebar_customer'


def register_cors_handlers():
    check_request_enabled.connect(
        cors_allow_zendesk_sidebar,
        dispatch_uid='thunderbird_accounts.core.cors_allow_zendesk_sidebar',
    )
