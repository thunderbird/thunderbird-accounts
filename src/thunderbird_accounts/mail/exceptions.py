from pydantic import ValidationError
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

class AccountSetError(StalwartError):
    """Raise when an individual is not found in Stalwart"""

    type: str
    description: Optional[str] = None
    fields: Optional[list] = None

    def __init__(self, type, description, fields, *args, **kwargs):
        super().__init__(args, kwargs)
        self.type = type
        self.description = description
        self.fields = fields

    def __str__(self):
        return f'AccountSetError: {self.type} : {self.description or self.fields}'


class AccessTokenNotFound(StalwartError):
    def __str__(self):
        return f'AccessTokenNotFoundError: {self.details}'


class DomainAlreadyExistsError(StalwartError):
    """Raise when a domain already exists in Stalwart"""

    domain: str

    def __init__(self, domain, *args, **kwargs):
        super().__init__(args, kwargs)
        self.domain = domain

    def __str__(self):
        return f'DomainAlreadyExistsError: {self.domain}'


class FailedToCreateDKIM(StalwartError):
    """Raise when Stalwart fails to create a DKIM key."""

    algorithm: str
    domain: str

    def __init__(self, algorithm, domain, details=None, *args, **kwargs):
        super().__init__(details, *args, **kwargs)
        self.algorithm = algorithm
        self.domain = domain

    def __str__(self):
        return f'FailedToCreateDKIM: {self.algorithm} for {self.domain}'


class FailedToReloadStalwart(StalwartError):
    """Raise when Stalwart fails to reload persisted changes."""

    domain: str
    algorithm: str | None

    def __init__(self, domain, details=None, algorithm=None, *args, **kwargs):
        super().__init__(details, *args, **kwargs)
        self.domain = domain
        self.algorithm = algorithm

    def __str__(self):
        context = f' after {self.algorithm} DKIM creation' if self.algorithm else ''
        return f'FailedToReloadStalwart: {self.domain}{context}'


class HostedDkimPublishRetry(Exception):
    """Raise when hosted DKIM publication should be retried."""

    domain: str
    phase: str  # Phase of update where exception happened.
    reason: str
    context: dict

    def __init__(self, domain: str, phase: str, reason: str = 'Unknown', error_type: str | None = None):
        self.domain = domain
        self.phase = phase
        self.reason = reason or 'Unknown'
        self.error_type = error_type
        self.context = {key: getattr(self, key) for key in ('domain', 'phase', 'reason', 'error_type')}
        super().__init__(self.context)

    def __str__(self):
        return f'HostedDkimPublishRetry: {self.phase} failed for {self.domain}: {self.reason}'


class HostedDkimDeleteRetry(Exception):
    """Raise when hosted DKIM deletion should be retried."""

    domain: str
    phase: str  # Phase of delete where exception happened.
    reason: str
    context: dict

    def __init__(self, domain: str, phase: str, reason: str = 'Unknown', error_type: str | None = None):
        self.domain = domain
        self.phase = phase
        self.reason = reason or 'Unknown'
        self.error_type = error_type
        self.context = {key: getattr(self, key) for key in ('domain', 'phase', 'reason', 'error_type')}
        super().__init__(self.context)

    def __str__(self):
        return f'HostedDkimDeleteRetry: {self.phase} failed for {self.domain}: {self.reason}'


class EmailNotValidError(RuntimeError):
    """Raises in utils.validate_email"""

    email: str
    error_message: str

    def __init__(self, email, error_message, *args, **kwargs):
        super().__init__(args, kwargs)
        self.email = email
        self.error_message = error_message

    def __str__(self):
        return f'EmailNotValidError: {self.email}, {self.error_message}'


class InvalidJMapResponseError(RuntimeError):
    """This is a generic pydantic response error. You should not get this, if you do there's a developer problem."""
    validation_error: ValidationError

    def __init__(self, validation_error):
        self.validation_error = validation_error
