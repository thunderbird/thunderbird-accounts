from functools import wraps

from django.conf import settings
from django.http import JsonResponse
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


def active_subscription_required(function=None, *, error_message=None, status=403):
    """Require an authenticated user with an active subscription."""

    def decorator(view_func):
        @wraps(view_func)
        def _view_wrapper(request, *args, **kwargs):
            if getattr(request.user, 'has_active_subscription', False):
                return view_func(request, *args, **kwargs)

            message = error_message or _('An active subscription is required.')
            return JsonResponse({'success': False, 'error': str(message)}, status=status)

        return _view_wrapper

    if function:
        return decorator(function)
    return decorator
