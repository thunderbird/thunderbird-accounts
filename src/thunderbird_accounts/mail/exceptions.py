from typing import Optional


class StalwartError(RuntimeError):
    """Generic error"""

    details: Optional[str]

    def __init__(self, details, *args, **kwargs):
        super().__init__(args, kwargs)
        if details:
            self.details = details
        else:
            self.details = 'Unknown'

    def __str__(self):
        return f'StalwartError: {self.details}'


class DomainNotFoundError(StalwartError):
    """Raise when a domain is not found in Stalwart"""

    domain: str

    def __init__(self, domain, *args, **kwargs):
        super().__init__(args, kwargs)
        self.domain = domain

    def __str__(self):
        return f'DomainNotFoundError: {self.domain}'


class AccountNotFoundError(StalwartError):
    """Raise when an individual is not found in Stalwart"""

    username: str

    def __init__(self, username, *args, **kwargs):
        super().__init__(args, kwargs)
        self.username = username

    def __str__(self):
        return f'AccountNotFoundError: {self.username}'


class AccessTokenNotFound(StalwartError):
    def __str__(self):
        return f'AccessTokenNotFoundError: {self.details}'
