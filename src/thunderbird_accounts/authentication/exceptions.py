from typing import Optional


class KeycloakError(RuntimeError):
    """Generic error"""

    details: Optional[str]

    def __init__(self, details, *args, **kwargs):
        super().__init__(args, kwargs)
        if details:
            self.details = details
        else:
            self.details = 'Unknown'

    def __str__(self):
        return f'Keycloak Error: {self.details}'


class InvalidDomainError(KeycloakError):
    username: str

    def __init__(self, username, *args, **kwargs):
        super().__init__(args, kwargs)
        self.username = username

    def __str__(self):
        return f'InvalidDomainError: {self.username}'


class ImportUserError(KeycloakError):
    username: str
    error: str

    def __init__(self, error, username: Optional[str] = None, *args, **kwargs):
        super().__init__(args, kwargs)
        self.username = username
        self.error = error

    def __str__(self):
        return f'ImportUserError: {self.error} for {self.username}'


class UpdateUserError(KeycloakError):
    username: str
    error: str

    def __init__(self, error, username: Optional[str] = None, *args, **kwargs):
        super().__init__(args, kwargs)
        self.username = username
        self.error = error

    def __str__(self):
        return f'UpdateUserError: {self.error} for {self.username}'


class DeleteUserError(KeycloakError):
    oidc_id: str
    error: str

    def __init__(self, error, oidc_id: Optional[str] = None, *args, **kwargs):
        super().__init__(args, kwargs)
        self.oidc_id = oidc_id
        self.error = error

    def __str__(self):
        return f'DeleteUserError: {self.error} for {self.oidc_id}'


class SendExecuteActionsEmailError(KeycloakError):
    oidc_id: Optional[str] = None
    action: str
    error: str

    def __init__(self, error, action: Optional[str] = None, oidc_id: Optional[str] = None, *args, **kwargs):
        super().__init__(args, kwargs)
        self.action = action
        self.error = error
        self.oidc_id = oidc_id

    def __str__(self):
        return f'SendExecuteActionsEmailError: {self.error} for {self.action}. <keycloak-id:{self.oidc_id}>'
