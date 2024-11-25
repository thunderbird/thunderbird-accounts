from urllib3 import util
from rest_framework.permissions import BasePermission

from thunderbird_accounts.client.models import ClientEnvironment


class IsClient(BasePermission):
    """
    Allows access only to Clients matching secret, host, and activeness.
    """

    def has_permission(self, request, view):
        host = request.get_host()
        parsed_host = util.parse_url(host)
        client_secret = request.POST.get('secret')
        if not client_secret:
            return False

        try:
            client_env = ClientEnvironment.objects.get(auth_token=client_secret)
        except ClientEnvironment.DoesNotExist:
            return False

        parsed_redirect_url = util.parse_url(client_env.redirect_url)
        is_host_valid = parsed_redirect_url.hostname == parsed_host.hostname

        # Check if the client env is not active, or if the host is valid
        if not client_env.is_active or not is_host_valid:
            return False

        # Append client_env to request
        request.client_env = client_env

        return True
