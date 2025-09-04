from thunderbird_accounts.mail.clients import MailClient


def inject_stalwart_client(func):
    """Inject an initialized stalwart mailclient"""

    def _inject_stalwart_client(*args, **kwargs):
        kwargs['stalwart'] = MailClient()
        return func(*args, **kwargs)

    return _inject_stalwart_client
