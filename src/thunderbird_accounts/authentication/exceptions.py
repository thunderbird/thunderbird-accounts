from typing import Optional


POSTGRES_DUPLICATE_KEY_MARKER = 'duplicate key value violates unique constraint'


def is_already_exists_error(
    *,
    status_code: Optional[int] = None,
    error_code: Optional[str] = None,
    error_desc: Optional[str] = None,
    error: Optional[str] = None,
) -> bool:
    # HTTP 409 means "Conflict" and is returned by Keycloak when a resource already exists.
    if status_code == 409:
        return True

    error_text = ' '.join(filter(None, [error_code, error_desc, error])).lower()
    return POSTGRES_DUPLICATE_KEY_MARKER in error_text


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

    def __init__(
        self,
        error,
        username: Optional[str] = None,
        error_code: Optional[str] = None,
        error_desc: Optional[str] = None,
        status_code: Optional[int] = None,
        *args,
        **kwargs,
    ):
        super().__init__(args, kwargs)
        self.username = username
        # Used for __str__
        self.error = error
        # Structured error from keycloak
        self.error_code = error_code
        self.error_desc = error_desc
        self.status_code = status_code

    @property
    def is_already_exists(self):
        return is_already_exists_error(
            status_code=self.status_code,
            error_code=self.error_code,
            error_desc=self.error_desc,
            error=self.error,
        )

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


class UpdateUserPlanInfoError(KeycloakError):
    username: str
    error: str

    def __init__(self, error, oidc_id: Optional[str] = None, *args, **kwargs):
        super().__init__(args, kwargs)
        self.oidc_id = oidc_id
        self.error = error

    def __str__(self):
        return f'UpdateUserError: {self.error} for {self.oidc_id}'


class GetUserError(KeycloakError):
    oidc_id: str
    error: str

    def __init__(self, error, oidc_id: Optional[str] = None, *args, **kwargs):
        super().__init__(args, kwargs)
        self.oidc_id = oidc_id
        self.error = error

    def __str__(self):
        return f'GetUserError: {self.error} for {self.oidc_id}'


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


class MfaCredentialError(KeycloakError):
    """Raised when the keycloak-mfa-rest provider rejects a credential operation
    with a client error (e.g. an invalid TOTP code, or an authenticator that is
    already configured). Carries the machine error code returned by the provider
    so callers can map it to a user-facing message."""

    def __init__(self, error_code, *args, **kwargs):
        super().__init__(error_code, *args, **kwargs)
        self.error_code = error_code

    def __str__(self):
        return f'MfaCredentialError: {self.error_code}'


class MfaStepUpRequiredError(KeycloakError):
    """Raised when the keycloak-mfa-rest provider rejects a sensitive mutation with
    401 ``step_up_required``: the forwarded user token does not prove a recent
    second-factor authentication. Callers should respond with the MFA
    reauthentication (step-up) redirect so the user can re-verify."""

    def __init__(self, *args, **kwargs):
        super().__init__('step_up_required', *args, **kwargs)

    def __str__(self):
        return 'MfaStepUpRequiredError: the provider requires a recent second-factor authentication'


class MfaSessionExpiredError(KeycloakError):
    """Raised when the keycloak-mfa-rest provider rejects a request with a plain 401
    (no ``step_up_required`` marker): the forwarded user OIDC access token is missing,
    invalid, or expired. This is distinct from a step-up demand — the access token's
    short lifetime can lapse while a user lingers in the setup flow. Callers should ask
    the user to sign in again rather than surfacing a generic upstream failure."""

    def __init__(self, *args, **kwargs):
        super().__init__('session_expired', *args, **kwargs)

    def __str__(self):
        return 'MfaSessionExpiredError: the forwarded user access token is missing or expired'


class AuthenticationUnavailable(RuntimeError):
    """Used in AccountsOIDCBackend to indicate we need to show a service unavailable page."""

    pass
