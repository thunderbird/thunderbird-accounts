from django.conf import settings

try:
    from paddle_billing import Client, Options, Environment
except ImportError:
    Client = None
    Options = None
    Environment = None


def inject_paddle(func):
    """Inject an initialized Paddle Client into a function as ``paddle``.
    If the paddle python sdk is not installed this will return None."""

    def _inject_paddle(*args, **kwargs):
        if Options:
            options = Options(Environment.SANDBOX if settings.PADDLE_ENV == 'sandbox' else Environment.PRODUCTION)
        else:
            options = None

        kwargs['paddle'] = Client(settings.PADDLE_API_KEY, options=options) if Client else None
        func(*args, **kwargs)

    return _inject_paddle
