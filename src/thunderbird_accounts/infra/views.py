from django.http import HttpRequest, HttpResponse


def health_check(request: HttpRequest):
    """Do nothing, only prove the service is responsive."""

    return HttpResponse('Aliveness demonstrated!')