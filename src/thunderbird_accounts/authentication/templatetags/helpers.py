import logging

from django import template
from django.conf import settings
from django.urls import reverse

from thunderbird_accounts.authentication import utils
from thunderbird_accounts.client.models import ClientEnvironment, Client

register = template.Library()


@register.simple_tag
def get_admin_login_code():
    admin_client = Client.objects.get(name=settings.ADMIN_CLIENT_NAME)
    admin_client_env = admin_client.clientenvironment_set.first()
    return utils.create_login_code(admin_client_env)
