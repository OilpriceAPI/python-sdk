"""Shared Energy Intelligence response-envelope handling (#107).

The EI controllers use two outer envelopes:

* ``{"data": ..., "meta": {...}}`` — rig counts, oil inventories, OPEC
  production, drilling productivity, forecasts.
* ``{"status": "success", "data": {...}}`` — well permits, frac focus.

Inside ``data``, a *collection* endpoint does not return a bare list. It
returns an object whose named key holds the list, alongside the parameters
the server echoed back (``report_date``, ``region``, ``series_code``, …).
``/v1/ei/rig_counts/by_basin`` returns ``{report_date, basins:[...]}``; the
list lives under ``basins``.

This module is the single place that knows that. It replaces the
``if "data" in response: return response["data"]`` line that was repeated in
every EI method and that silently handed the caller the envelope object where
the signature promised a list.
"""

from typing import Any, Dict, List, Optional

from ...exceptions import OilPriceAPIError

__all__ = ["ei_data", "unwrap_ei_collection", "unwrap_ei_object"]


def ei_data(response: Any) -> Any:
    """Strip the outer ``data`` envelope when there is one.

    Used by the EI methods whose payload genuinely *is* the object or list
    sitting directly under ``data``. Anything that is not a mapping is handed
    back untouched, so a bare-list response still works.
    """
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def _locate_collection(response: Any, collection: str) -> Optional[Any]:
    """Find the named collection, tolerating every shape the API has shipped."""
    if isinstance(response, list):
        return response
    if not isinstance(response, dict):
        return None

    # A pre-envelope response that names the collection at the top level.
    if "data" not in response and collection in response:
        return response[collection]

    data = ei_data(response)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and collection in data:
        return data[collection]
    return None


def unwrap_ei_collection(
    response: Any,
    *,
    collection: str,
    subject: str,
) -> List[Dict[str, Any]]:
    """Return the named collection as a list of records.

    Args:
        response: The decoded response body.
        collection: The key the server puts the list under, e.g. ``"basins"``.
        subject: Human-readable name of the endpoint, used in the error.

    Returns:
        The list of records. An empty collection is an empty list.

    Raises:
        OilPriceAPIError: If the collection is missing, is not a list, or
            contains something other than records. A malformed success body is
            reported, never silently turned into an empty result.
    """
    rows = _locate_collection(response, collection)

    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise OilPriceAPIError(
            "Malformed %s response: expected a %s list" % (subject, collection),
            code="MALFORMED_RESPONSE",
            raw_body=response,
        )
    return rows


def unwrap_ei_object(
    response: Any,
    *,
    subject: str,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a single record from an EI response.

    Args:
        response: The decoded response body.
        subject: Human-readable name of the endpoint, used in the error.
        key: The key the record is nested under, when the endpoint nests it
            (``well_permit``, ``frac_focus_disclosure``). When the key is
            absent from the payload the payload itself is returned, so the
            older flat shape keeps working.

    Raises:
        OilPriceAPIError: If the payload is not a record.
    """
    data = ei_data(response)

    if key is not None and isinstance(data, dict) and key in data:
        data = data[key]

    if not isinstance(data, dict):
        raise OilPriceAPIError(
            "Malformed %s response: expected a %s object"
            % (subject, key or "record"),
            code="MALFORMED_RESPONSE",
            raw_body=response,
        )
    return data
