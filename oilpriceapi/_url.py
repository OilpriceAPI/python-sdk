"""Pin every request to the configured API origin (#102).

The clients used to build a request URL with a bare
``urljoin(base_url + "/", path)``. ``urljoin`` implements RFC 3986 reference
resolution, so a caller-supplied raw path that happens to be a *network-path
reference* — anything starting ``//`` — replaces the authority outright:

    urljoin("https://api.oilpriceapi.com/", "//elsewhere.example/v1/prices")
    -> "https://elsewhere.example/v1/prices"

The client's ``Authorization`` header is set on the httpx client, not per
request, so the customer's API key travels to whatever host the caller's path
resolved to. ``//user@elsewhere.example/...`` is worse still: httpx reads the
userinfo and replaces the Token header with a Basic credential.

This module resolves the URL once, centrally, and refuses anything whose origin
(scheme, host, port) is not exactly the configured base origin. An explicit
``base_url`` — a proxy, a staging host, a test server — keeps working, because
the guard pins to whatever the caller configured, not to a hard-coded hostname.
"""

from __future__ import annotations

from typing import Any, Tuple
from urllib.parse import urljoin, urlsplit

from .exceptions import ConfigurationError, ValidationError

__all__ = ["resolve_api_url"]

# Backslash: several URL parsers (WHATWG browsers, some proxies and gateways)
# normalize "\" to "/", which turns "/\evil.example/x" into a network-path
# reference after this SDK has already decided it was a plain path.
# Control characters (including CR/LF and NUL) can split a request line or
# smuggle a header. Neither can appear in a legitimate API path.
#
# The range stops BELOW 0x20: U+0020 SPACE is legitimate in a path or an inline
# query string, httpx percent-encodes it, and it cannot introduce an authority
# or split a request line. `range(0x21)` forbade it and broke every caller who
# built a query inline -- including this SDK's own demo resource (#119).
_FORBIDDEN_CHARS = frozenset("\\") | frozenset(chr(c) for c in range(0x20)) | {chr(0x7F)}

_DEFAULT_PORTS = {"http": 80, "https": 443}


def _origin(url: str) -> Tuple[str, str, int]:
    """Return ``(scheme, host, port)``, never a raw ``ValueError``.

    ``urlsplit`` and its ``.hostname`` / ``.port`` accessors raise ValueError
    for an out-of-range port ("...:99999") and for a non-ASCII netloc whose
    NFKC normalisation introduces one of ``/?#@:`` ("https://\u2100evil.example").
    ``_origin`` runs on ``base_url`` on EVERY request, so a misconfigured client
    raised a bare stdlib exception from the hot path -- the one type this
    module's docstring says cannot escape (#123).
    """
    try:
        parts = urlsplit(url)
        scheme = (parts.scheme or "").lower()
        host = (parts.hostname or "").lower()
        port = parts.port or _DEFAULT_PORTS.get(scheme, 0)
    except ValueError as exc:
        raise ConfigurationError(
            f"Cannot parse the URL {url!r}: {exc}. "
            "Check the client's base_url -- it must be an absolute "
            "http(s) origin such as 'https://api.oilpriceapi.com'."
        ) from exc
    return scheme, host, port


def _reject(path: Any, reason: str) -> "ValidationError":
    # `path` is caller-supplied and carries no credential; the API key lives in
    # a header, never in the path, so echoing it back is safe and is the only
    # way the caller can see which value was refused.
    return ValidationError(
        message=(
            f"Refusing to send this request: the path {reason}. "
            "API paths must be relative to the configured base URL "
            "(for example '/v1/prices/latest'). To talk to a different host, "
            "construct a client with that base_url instead — a raw path may "
            "not change the origin, because the API key would be sent to it."
        ),
        field="path",
        value=path,
        # No request was sent, so there is no HTTP status to report. The 422
        # default would make this local refusal indistinguishable, to any log
        # or metric keyed on status, from a 422 the API actually returned.
        status_code=None,
    )


def resolve_api_url(base_url: str, path: Any) -> str:
    """Resolve ``path`` against ``base_url``, refusing any origin change.

    Args:
        base_url: The client's configured base URL (no trailing slash).
        path: Caller-supplied API path.

    Returns:
        The absolute URL to request, guaranteed to share ``base_url``'s origin.

    Raises:
        ValidationError: If ``path`` is not a string, contains a character that
            a URL parser could use to change the authority, or resolves to any
            origin other than ``base_url``'s.
    """
    if not isinstance(path, str):
        raise _reject(path, f"must be a string, got {type(path).__name__}")

    if not path:
        raise _reject(path, "is empty")

    bad = _FORBIDDEN_CHARS.intersection(path)
    if bad:
        raise _reject(
            path,
            "contains a character that is not allowed in an API path "
            f"({''.join(sorted(repr(c) for c in bad))})",
        )

    if "//" in path.split("?", 1)[0].split("#", 1)[0]:
        # Covers the plain scheme-relative "//host/..." form and any absolute
        # URL ("https://host/..."), before it can be resolved.
        raise _reject(path, "may not contain '//'")

    normalized = path if path.startswith("/") else "/" + path

    # urljoin parses the base, so it raises the same ValueError _origin does
    # for an out-of-range port or an NFKC-invalid netloc -- and it runs first.
    try:
        url = urljoin(base_url + "/", normalized)
    except ValueError as exc:
        raise ConfigurationError(
            f"Cannot parse the client's base_url {base_url!r}: {exc}. "
            "It must be an absolute http(s) origin such as "
            "'https://api.oilpriceapi.com'."
        ) from exc

    if _origin(url) != _origin(base_url):
        raise _reject(path, "resolves to a different host than the configured base URL")

    return url
