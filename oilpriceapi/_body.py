"""Decode a successful response body, tolerating a legitimately empty one (#103).

Both clients used to parse every 2xx with a bare ``response.json()``. The Rails
webhooks controller answers ``destroy`` with ``head :no_content`` -- a 204 with
an empty body -- so ``client.webhooks.delete(...)`` raised ``JSONDecodeError``.
The deletion had SUCCEEDED and the caller was told it failed, which is the worst
shape of error for a mutation: the obvious recovery is to retry a delete that
already worked.

The rule is deliberately narrow. An empty body on a 2xx is success. A malformed
NON-EMPTY body is still an error -- that is a real parse failure and laundering
it into an empty success would hide a broken response.
"""

from __future__ import annotations

from typing import Any, Dict

import httpx

__all__ = ["decode_json_body"]


def decode_json_body(response: httpx.Response) -> Dict[str, Any]:
    """Return the decoded 2xx body, or ``{}`` when the server sent none.

    Args:
        response: A response whose status is already known to be 2xx.

    Returns:
        The decoded JSON body, or an empty dict for a no-content response.

    Raises:
        Whatever ``response.json()`` raises for a non-empty body that is not
        valid JSON. A malformed response is still a failure.
    """
    # Decode first and inspect the body only when that fails. Checking
    # `.content` up front would touch the body on every successful request --
    # needless work on the hot path, and it makes the helper sensitive to how a
    # response is represented rather than to what it contains.
    try:
        return response.json()
    except ValueError:
        # 204 No Content and 304 Not Modified are DEFINED to carry no body, and
        # some servers answer a mutation with a zero-length 200 or 202. A body
        # of only whitespace is as empty as a zero-length one. In every one of
        # those cases the request SUCCEEDED and there is simply nothing to
        # decode, so an empty dict is the honest answer.
        if not (response.content or b"").strip():
            return {}
        # A malformed NON-EMPTY body is a real parse failure. Laundering it into
        # an empty success would hide a broken response from the caller.
        raise
