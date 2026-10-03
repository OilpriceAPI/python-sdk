"""Guard for SDK methods whose API route does not exist.

Each of these methods used to send a request to a path the API has never
routed, so every call came back as a 404 that read like a data problem
(#153). They now fail locally, before any request is sent, and name the
supported replacement.
"""

import warnings
from typing import NoReturn

from ..exceptions import ValidationError


def removed_endpoint(method: str, alternative: str) -> NoReturn:
    """Warn and raise for a method with no backing API route.

    Args:
        method: Public method name, e.g. ``"client.drilling.trends()"``.
        alternative: The supported call to use instead.

    Raises:
        ValidationError: Always, with ``code="ENDPOINT_NOT_AVAILABLE"`` and
            ``status_code=None`` because no request was sent.
    """
    message = (
        f"{method} is not available: the API has no route for it. "
        f"Use {alternative} instead. This method will be removed in 2.0."
    )
    warnings.warn(message, DeprecationWarning, stacklevel=3)
    raise ValidationError(
        message,
        status_code=None,
        code="ENDPOINT_NOT_AVAILABLE",
    )
