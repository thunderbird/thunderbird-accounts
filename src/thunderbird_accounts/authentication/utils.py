from django.conf import settings


def is_email_in_allow_list(email: str):
    allow_list = settings.AUTH_ALLOW_LIST
    if not allow_list:
        return True

    return email.endswith(tuple(allow_list.split(',')))
