import logging

from urllib3 import util
from rest_framework.permissions import BasePermission
from urllib3.exceptions import LocationParseError

from thunderbird_accounts.client.models import ClientEnvironment


class IsClient(BasePermission):
    """
    Allows access only to Clients matching secret, host, and activeness.
    """

    def has_permission(self, request, view):
        host = request.get_host()
        client_secret = request.data.get('secret')
        if not client_secret:
            return False

        try:
            client_env: ClientEnvironment = ClientEnvironment.objects.get(auth_token=client_secret)
        except ClientEnvironment.DoesNotExist:
            return False

        allowed_hostnames = client_env.allowed_hostnames

        is_host_valid = any(
            [
                allowed_hostname == host
                for allowed_hostname in allowed_hostnames
            ]
        )

        # Check if the client env is not active, or if the host is valid
        if not client_env.is_active or not is_host_valid:
            return False

        # Append client_env to request
        request.client_env = client_env

        return True
