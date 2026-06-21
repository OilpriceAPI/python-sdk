"""
Demo Resource

Public, no-authentication demo endpoints (``/v1/demo/*``). These power the
"time to first call" experience: a developer can fetch real free-tier prices
and the full commodity catalog without an API key.

The demo endpoints ignore authentication entirely, so :class:`DemoResource`
works both as an attribute of an authenticated client (``client.demo``) and
standalone with no key:

    >>> from oilpriceapi.resources.demo import DemoResource
    >>> demo = DemoResource()
    >>> data = demo.prices()
    >>> data["prices"][0]["code"]
    'BRENT_CRUDE_USD'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

if TYPE_CHECKING:
    from ..client import OilPriceAPI

DEFAULT_BASE_URL = "https://api.oilpriceapi.com"


class DemoResource:
    """Resource for the public, no-auth demo endpoints.

    Args:
        client: Optional authenticated :class:`OilPriceAPI`. When provided, the
            demo calls reuse that client's HTTP transport and base URL. When
            omitted, the resource issues its own unauthenticated requests so the
            demo works with no API key.
        base_url: Base URL used for standalone (no-client) requests.
        timeout: Request timeout (seconds) for standalone requests.
    """

    def __init__(
        self,
        client: Optional["OilPriceAPI"] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> Dict[str, Any]:
        """GET a demo path and return the parsed JSON envelope.

        Returns the full envelope ``{"status": ..., "data": {...}}`` so callers
        can assert on the contract.
        """
        if self.client is not None:
            # Reuse the authenticated client's transport. The demo endpoints
            # ignore the auth header, so this is harmless when a key is set.
            return self.client.request(method="GET", path=path)

        url = f"{self.base_url}{path}"
        response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        return data

    def prices(self, codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get latest demo prices for free-tier commodities.

        Args:
            codes: Optional list of commodity codes to request. When omitted,
                the API returns all free-tier commodities.

        Returns:
            The ``data`` payload: ``{"prices": [...], "meta": {...}, "examples": {...}}``.
        """
        path = "/v1/demo/prices"
        if codes:
            path = f"{path}?codes={','.join(codes)}"
        envelope = self._get(path)
        data: Dict[str, Any] = envelope.get("data", envelope)
        return data

    def commodities(self) -> Dict[str, Any]:
        """Get the full demo commodity catalog grouped by category.

        Returns:
            The ``data`` payload: ``{"commodities": {category: [...]}, "meta": {...}}``.
        """
        envelope = self._get("/v1/demo/commodities")
        data: Dict[str, Any] = envelope.get("data", envelope)
        return data
