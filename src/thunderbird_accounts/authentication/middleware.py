import time

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.http import HttpRequest
from socket import gethostbyname, gethostname

from ..client.models import ClientEnvironment


class FXABackend(BaseBackend):
    def authenticate(self, request, fxa_id=None, email=None):
        user_model = get_user_model()

        # First look-up by fxa id
        try:
            user = user_model.objects.get(fxa_id=fxa_id)
            if user.email != email:
                user.last_used_email = user.email
                user.email = email
                user.save()
        except user_model.DoesNotExist:
            user = None

        # If that doesn't work, look up by email
        if user is None:
            try:
                user = user_model.objects.get(email=email)
                user.fxa_id = fxa_id
                user.save()

            except user_model.DoesNotExist:
                user = None

        return user

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None


class ClientSetAllowedHostsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        print('---')
        start = time.perf_counter_ns()

        allowed_hosts = cache.get(settings.ALLOWED_HOSTS_CACHE_KEY)
        if not allowed_hosts:
            allowed_hosts = ClientEnvironment.cache_hostnames()
        # Get the IP of whatever machine is running this code and allow it as a hostname
        allowed_hosts.append(gethostbyname(gethostname()))

        settings.ALLOWED_HOSTS = allowed_hosts

        end = time.perf_counter_ns()

        print(f'> total time {(end-start) / 1000000} ms')

        response = self.get_response(request)

        return response
