class DomainNotFoundError(RuntimeError):
    """Raise when a domain is not found in Stalwart"""

    domain: str

    def __init__(self, domain, *args, **kwargs):
        super().__init__(args, kwargs)
        self.domain = domain


class AccountNotFoundError(RuntimeError):
    """Raise when an individual is not found in Stalwart"""

    username: str

    def __init__(self, username, *args, **kwargs):
        super().__init__(args, kwargs)
        self.username = username
