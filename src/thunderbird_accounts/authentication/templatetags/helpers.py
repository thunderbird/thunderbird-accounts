import json

from django import template


register = template.Library()


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
