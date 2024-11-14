import logging

from django import template
from django.urls import reverse

from thunderbird_accounts.authentication import utils
from thunderbird_accounts.client.models import ClientEnvironment

register = template.Library()


@register.simple_tag
def get_admin_login_code():
    # TODO: Figure out a better way to retrieve admin_client
    admin_client = ClientEnvironment.objects.filter(redirect_url=reverse('admin:index')).first()
    return utils.create_login_code(admin_client)
