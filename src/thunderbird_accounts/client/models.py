import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.utils.models import BaseModel


class ClientEnvironment(BaseModel):
    """An environment associated with a client. Each environment requires a redirect_url and gets an auth_token.

    :param environment: The environment type (e.g. dev, stage, prod)
    :param redirect_url: URL to redirect the login request back to
    :param auth_token: The authentication token given to a client so they can make server-to-server requests with us
    :param is_active: Is this environment active?"""
    environment = models.CharField(max_length=128, default='prod', help_text=_('The environment (e.g. dev, stage, prod)'))
    redirect_url = models.CharField(max_length=2048, help_text=_('The redirect url back to the client after login'))
    auth_token = models.CharField(max_length=256, null=True, help_text=_('The server-to-server/secret auth token'))
    is_active = models.BooleanField(default=True, help_text=_('Is this environment active?'))

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['environment']),
            models.Index(fields=['is_active'])
        ]

    client = models.ForeignKey('Client', on_delete=models.CASCADE)


class ClientWebhook(BaseModel):
    """A webhook associated with a client's environment. Webhooks are required in every environment except for dev.

    :param name: The name of the webhook (admin purposes)
    :param webhook_url: The URL where we should send our POST requests
    :param type: The type of webhook"""
    class WebhookType(models.TextChoices):
        AUTH = 'auth', _('Auth')
        SUBSCRIPTION = 'subscription', _('Subscription')

    name = models.CharField(max_length=128, help_text=_('The name of the webhook (for admin purposes)'))
    webhook_url = models.CharField(max_length=2048, help_text=_('The URL of the webhook'))
    type = models.CharField(
        max_length=32,
        choices=WebhookType,
        help_text=_('What type of webhook is it?')
    )

    client_environment = models.ForeignKey('ClientEnvironment', on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['name']),
            models.Index(fields=['webhook_url']),
            models.Index(fields=['type']),
        ]


class ClientContact(BaseModel):
    """A contact for a client for auditing / service info purposes. At least one should be required.

    :param name: How the contact should be addressed. Can be full name, partial name, internet handle, etc...
    :param email: An up-to-date active email address we could send service alerts to
    :param website: A website (can be tied to the environment, but not required)
    """
    name = models.CharField(max_length=128, help_text=_('How the contact should be addressed'))
    email = models.CharField(max_length=128, help_text=_('The email to reach the contact'))
    website = models.CharField(max_length=2048, help_text=_('The website for the contact'))

    client = models.ForeignKey('Client', on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['name']),
            models.Index(fields=['email']),
        ]


class Client(BaseModel):
    """An API client. Each client will contain many environments which will be given an authentication token to send
    us requests with. These requests should be server-to-server only.

    :param name: The name of the client.
    """
    name = models.CharField(max_length=128, unique=True, help_text=_('Client\'s name (must be unique.)'))

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'Client {self.name}'
