from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend


class FXABackend(BaseBackend):
    def authenticate(self, request, fxa_id=None, email=None):
        user_model = get_user_model()

        # First look-up by fxa uid
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
