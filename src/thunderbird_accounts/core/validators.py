from django.core.exceptions import ValidationError
from django.core.validators import validate_domain_name


def normalize_custom_domain(domain_name: str | None) -> str | None:
    """Normalize and validate a custom mail domain."""
    if not isinstance(domain_name, str):
        return None

    domain = ''.join(ch.lower() for ch in domain_name if not ch.isspace())
    if not domain or domain.endswith('.'):
        return None

    try:
        validate_domain_name(domain)
    except ValidationError:
        return None

    return domain


def is_valid_custom_domain(domain_name: str | None) -> bool:
    return normalize_custom_domain(domain_name) is not None
