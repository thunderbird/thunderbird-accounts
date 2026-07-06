from functools import wraps

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

try:
    from paddle_billing import Client, Options, Environment
except ImportError:
    Client = None
    Options = None
    Environment = None


def init_paddle():
    if Options:
        options = Options(Environment.SANDBOX if settings.PADDLE_ENV == 'sandbox' else Environment.PRODUCTION)
    else:
        options = None

    if not settings.PADDLE_API_KEY or not Client:
        return None

    return Client(settings.PADDLE_API_KEY, options=options)


def inject_paddle(func):
    """Inject an initialized Paddle Client into a function as ``paddle``.
    If the paddle python sdk is not installed this will return None."""

    def _inject_paddle(*args, **kwargs):
        kwargs['paddle'] = init_paddle()

        return func(*args, **kwargs)

    return _inject_paddle


def active_subscription_required(function=None, *, error_message=None, response_data=None, status=403):
    """Require an authenticated user with an active subscription."""

    def decorator(view_func):
        @wraps(view_func)
        def _view_wrapper(request, *args, **kwargs):
            if getattr(request.user, 'has_active_subscription', False):
                return view_func(request, *args, **kwargs)

            if _wants_json_response(request):
                message = error_message or _('An active subscription is required.')
                data = response_data if response_data is not None else {'success': False, 'error': str(message)}
                return JsonResponse(data, status=status)

            return HttpResponseRedirect(reverse('vue_app'))

        return _view_wrapper

    if function:
        return decorator(function)
    return decorator


def _wants_json_response(request):
    accept = request.headers.get('Accept', '')
    content_type = request.headers.get('Content-Type', '')

    if _has_json_media_type(accept) or _has_json_media_type(content_type):
        return True

    # Existing fetch calls often rely on the browser default Accept: */*,
    # and RequestFactory tests often omit Accept entirely.
    return not accept or accept.strip() == '*/*'


def _has_json_media_type(header_value):
    for value in header_value.split(','):
        media_type = value.split(';', 1)[0].strip().lower()
        if media_type == 'application/json' or media_type.endswith('+json'):
            return True
    return False
