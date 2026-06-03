"""Reserved local-part lists and the :func:`is_reserved` check.

The matching logic lives in ``checker.py``; the vendored word lists and the
``update.py`` maintenance script live alongside it. See ``README.md``.
"""

from thunderbird_accounts.authentication.reserved.checker import is_reserved

__all__ = ['is_reserved']
