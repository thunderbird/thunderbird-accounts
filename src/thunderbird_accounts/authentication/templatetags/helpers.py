import json

from django import template
from django.conf import settings


from thunderbird_accounts.authentication import utils
from thunderbird_accounts.client.models import Client

register = template.Library()


@register.simple_tag
def get_admin_login_code():
    admin_client = Client.objects.get(name=settings.ADMIN_CLIENT_NAME)
    admin_client_env = admin_client.clientenvironment_set.first()
    return utils.create_login_code(admin_client_env)


@register.filter
def to_json(val):
    return json.dumps(val)


@register.simple_tag(takes_context=True)
def get_form_error_message(context):
    """Searches the message bag for the first message tagged with 'form-error'."""
    messages = context.get('messages')
    if not messages:
        return None
    for message in messages:
        if 'form-error' in message.tags:
            return message.message
    return None
