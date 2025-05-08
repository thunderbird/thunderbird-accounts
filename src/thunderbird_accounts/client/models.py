import logging
import secrets
from urllib.parse import urlparse
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.db.models.functions.text import Lower
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.utils.models import BaseModel


def _generate_secret():
    """Generate an access token for the auth_token field as the default value"""
    return secrets.token_hex(64)


class ClientEnvironment(BaseModel):
    """An environment associated with a client. Each environment requires a redirect_url and gets an auth_token.

    :param environment: The environment type (e.g. dev, stage, prod)
    :param redirect_url: URL to redirect the login request back to
    :param auth_token: The authentication token given to a client so they can make server-to-server requests with us
    :param is_active: Is this environment active?"""

    environment = models.CharField(
        max_length=128, default='prod', help_text=_('The environment (e.g. dev, stage, prod)')
    )
    redirect_url = models.CharField(max_length=2048, help_text=_('The redirect url back to the client after login'))
    auth_token = models.CharField(
        max_length=256,
        null=True,
        help_text=_('The server-to-server/secret auth token'),
        unique=True,
        default=_generate_secret,
    )
    is_active = models.BooleanField(default=True, help_text=_('Is this environment active?'))
    allowed_hostnames = models.JSONField(
        default=list,
        null=False,
        help_text=_('List of allowed hostnames for this client environment.'),
    )
    is_public = models.BooleanField(
        default=True,
        help_text=_('Are non-users allowed to sign up? Otherwise an allow list is checked.'),
        db_index=True,
    )

    class Meta(BaseModel.Meta):
        indexes = [*BaseModel.Meta.indexes, models.Index(fields=['environment']), models.Index(fields=['is_active'])]
        constraints = [
            UniqueConstraint(
                Lower('environment').desc(), 'redirect_url', name='unique_lower_environment_and_redirect_url'
            )
        ]

    client = models.ForeignKey('Client', on_delete=models.CASCADE)

    @classmethod
    def cache_hostnames(cls):
        client_envs = ClientEnvironment.objects.filter(environment=settings.APP_ENV).all()
        allowed_hosts = []
        allowed_origins = []

        for env in client_envs:
            hostnames = env.allowed_hostnames
            for hostname in hostnames:
                try:
                    parsed_redirect_url = urlparse(env.redirect_url)
                    # Retrieve the scheme off the redirect url for now...
                    scheme = parsed_redirect_url.scheme or 'https'

                    parsed_url = urlparse(f'{scheme}://{hostname}')
                except ValueError as ex:
                    logging.warning(f'[cache_hostnames] Bad hostname {hostname} / {ex}')
                    continue
                if parsed_url.netloc:
                    allowed_hosts.append(parsed_url.netloc)
                    allowed_origins.append(f'{scheme}://{parsed_url.netloc}')

        # Clear out any duplicates
        allowed_hosts = list(set(settings.ALLOWED_HOSTS + allowed_hosts))
        allowed_origins = list(set(settings.CORS_ALLOWED_ORIGINS + allowed_origins))

        cache.set(settings.ALLOWED_HOSTS_CACHE_KEY, allowed_hosts)
        cache.set(settings.ALLOWED_ORIGINS_CACHE_KEY, allowed_origins)

        logging.info(f'Caching allowed_hosts: {allowed_hosts}')
        logging.info(f'Caching cors_allowed_origins: {allowed_origins}')
        return allowed_hosts, allowed_origins

    def __str__(self):
        return f'Client Environment {self.environment} for {self.client.name}'


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
    type = models.CharField(max_length=32, choices=WebhookType, help_text=_('What type of webhook is it?'))
    secret = models.CharField(
        max_length=256,
        null=False,
        help_text=_('The server-to-server/secret webhook secret'),
        unique=True,
        default=_generate_secret,
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
    email = models.CharField(max_length=128, help_text=_('The email to reach the contact'), unique=True)
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

    name = models.CharField(max_length=128, unique=True, help_text=_("Client's name (must be unique.)"))

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'Client {self.name}'
