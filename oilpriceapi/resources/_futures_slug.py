"""
Futures slug normalization.

The OilPriceAPI futures endpoints are keyed by instrument-generic slugs, not by
exchange contract codes. The latest-curve route is ``GET /v1/futures/{slug}``
and the sub-resources are ``/v1/futures/{slug}/curve``, ``/historical``,
``/ohlc``, ``/intraday`` and ``/spread-history``. There is no ``?contract=``
route, so a caller passing a raw ticker such as ``"CL.1"`` would hit
``/v1/futures/CL.1`` and get a 404.

To keep the SDK friendly, callers may pass either:

* a canonical slug (``"brent"``, ``"wti"``, ``"natural-gas"``, ...),
* a legacy venue slug (``"ice-brent"``, ``"ice-wti"``, ...), or
* a familiar exchange/contract code (``"BZ"``, ``"CL"``, ``"NG"``, ...),

and :func:`normalize_futures_slug` resolves it to the canonical slug the API
expects. Continuous slugs (``"continuous/brent"``, ``"continuous/wti"``) are
passed through unchanged.

Mappings verified against the Rails API
(``app/controllers/v1/futures_controller.rb`` + ``config/routes.rb``).
"""

from typing import Dict, Set

# Canonical slugs emitted by the SDK for latest-curve routes.
VALID_SLUGS: Set[str] = {
    "brent",
    "wti",
    "gasoil",
    "natural-gas",
    "ttf-gas",
    "lng-jkm",
    "eu-carbon",
    "uk-carbon",
    "continuous/brent",
    "continuous/wti",
}

# Older public route names remain valid caller inputs, but the SDK emits the
# instrument-generic route so new traffic does not encode a reporting venue.
LEGACY_SLUG_TO_CANONICAL: Dict[str, str] = {
    "ice-brent": "brent",
    "ice-wti": "wti",
    "ice-gasoil": "gasoil",
    "eua-carbon": "eu-carbon",
}

# Friendly exchange/contract codes -> canonical instrument slug.
# Keys are matched case-insensitively against the leading contract symbol
# (e.g. "CL", "CL.1", "CL1!" all resolve to wti).
CONTRACT_CODE_TO_SLUG: Dict[str, str] = {
    "BZ": "brent",
    "BRENT": "brent",
    "CL": "wti",
    "WTI": "wti",
    "G": "gasoil",
    "QS": "gasoil",
    "GASOIL": "gasoil",
    "NG": "natural-gas",    # NYMEX Henry Hub natural gas
    "NATGAS": "natural-gas",
    "TTF": "ttf-gas",       # ICE TTF natural gas
    "JKM": "lng-jkm",       # ICE/CME JKM LNG
    "LNG": "lng-jkm",
    "EUA": "eu-carbon",
    "EU_CARBON": "eu-carbon",
    "UKA": "uk-carbon",     # ICE UKA (UK) carbon
    "UK_CARBON": "uk-carbon",
}


def normalize_futures_slug(contract: str) -> str:
    """Resolve a futures ``contract`` argument to the API's canonical slug.

    Accepts a canonical slug (returned unchanged), a continuous slug, or a
    friendly exchange/contract code (e.g. ``"BZ"``, ``"CL.1"``, ``"NG"``).

    Args:
        contract: A slug (``"brent"``) or a contract code (``"BZ"``).

    Returns:
        The instrument-generic slug the API expects (e.g. ``"brent"``).

    Raises:
        ValueError: If ``contract`` is empty or cannot be resolved.
    """
    if not contract or not str(contract).strip():
        raise ValueError("futures contract/slug must be a non-empty string")

    raw = str(contract).strip()
    lowered = raw.lower()

    # Already a canonical (or continuous) slug.
    if lowered in VALID_SLUGS:
        return lowered

    legacy_slug = LEGACY_SLUG_TO_CANONICAL.get(lowered)
    if legacy_slug is not None:
        return legacy_slug

    symbol = raw.upper()
    exact_code_slug = CONTRACT_CODE_TO_SLUG.get(symbol)
    if exact_code_slug is not None:
        return exact_code_slug

    # Contract code form: take the leading symbol before any month/order
    # suffix such as ".1", "1!", "-2025-12", "_2025_12".
    for sep in (".", "!", "-", "_", " "):
        if sep in symbol:
            symbol = symbol.split(sep, 1)[0]
    # Strip a trailing contract-order number (e.g. TradingView "CL1!" -> "CL1").
    symbol = symbol.rstrip("0123456789").strip()

    slug = CONTRACT_CODE_TO_SLUG.get(symbol)
    if slug is not None:
        return slug

    valid = ", ".join(sorted(VALID_SLUGS))
    codes = ", ".join(sorted(CONTRACT_CODE_TO_SLUG))
    raise ValueError(
        f"Unknown futures contract/slug {contract!r}. "
        f"Pass a slug ({valid}) or a contract code ({codes})."
    )
