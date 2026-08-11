from unittest.mock import AsyncMock, Mock

import pytest

from oilpriceapi.async_resources import AsyncEIWellPermitsResource
from oilpriceapi.exceptions import OilPriceAPIError
from oilpriceapi.resources.ei.well_permits import EIWellPermitsResource

PERMIT = {
    "api_number": "42329000000001",
    "state_code": "TX",
    "well": {"name": "Eagle 1"},
}


@pytest.mark.parametrize(
    "response",
    [
        [PERMIT],
        {"data": [PERMIT]},
        {"well_permits": [PERMIT], "meta": {"count": 1}},
        {"status": "success", "data": {"well_permits": [PERMIT], "meta": {"count": 1}}},
    ],
)
def test_search_accepts_live_filters_and_unwraps_supported_shapes(response) -> None:
    client = Mock()
    client.request.return_value = response
    resource = EIWellPermitsResource(client)

    permits = resource.search(states="TX", well_name="Eagle")

    assert permits == [PERMIT]
    client.request.assert_called_once_with(
        method="GET",
        path="/v1/ei/well-permits/search",
        params={"states": "TX", "well_name": "Eagle"},
    )


def test_search_keeps_legacy_query_parameter() -> None:
    client = Mock()
    client.request.return_value = {"data": [PERMIT]}
    resource = EIWellPermitsResource(client)

    assert resource.search("Eagle", states="TX") == [PERMIT]
    assert client.request.call_args.kwargs["params"] == {"states": "TX", "query": "Eagle"}


@pytest.mark.parametrize(
    "response",
    [
        {"status": "success", "data": {"items": []}},
        {"status": "success"},
        "unexpected response",
    ],
)
def test_search_rejects_unknown_success_shapes(response) -> None:
    client = Mock()
    client.request.return_value = response
    resource = EIWellPermitsResource(client)

    with pytest.raises(OilPriceAPIError, match="well_permits") as error:
        resource.search(states="TX")

    assert error.value.code == "MALFORMED_RESPONSE"


def test_search_accepts_an_explicit_empty_result() -> None:
    client = Mock()
    client.request.return_value = {
        "status": "success",
        "data": {"well_permits": [], "meta": {"count": 0}},
    }

    assert EIWellPermitsResource(client).search(states="TX") == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        [PERMIT],
        {"data": [PERMIT]},
        {"well_permits": [PERMIT], "meta": {"count": 1}},
        {"status": "success", "data": {"well_permits": [PERMIT], "meta": {"count": 1}}},
    ],
)
async def test_async_search_accepts_live_filters_and_unwraps_supported_shapes(response) -> None:
    client = Mock()
    client.request = AsyncMock(return_value=response)
    resource = AsyncEIWellPermitsResource(client)

    permits = await resource.search(states="TX", well_name="Eagle")

    assert permits == [PERMIT]
    client.request.assert_awaited_once_with(
        method="GET",
        path="/v1/ei/well-permits/search",
        params={"states": "TX", "well_name": "Eagle"},
    )


@pytest.mark.asyncio
async def test_async_search_keeps_legacy_query_parameter() -> None:
    client = Mock()
    client.request = AsyncMock(return_value={"data": [PERMIT]})
    resource = AsyncEIWellPermitsResource(client)

    assert await resource.search("Eagle", states="TX") == [PERMIT]
    assert client.request.call_args.kwargs["params"] == {"states": "TX", "query": "Eagle"}


@pytest.mark.asyncio
async def test_async_search_rejects_unknown_success_shape() -> None:
    client = Mock()
    client.request = AsyncMock(return_value={"status": "success", "data": {"items": []}})
    resource = AsyncEIWellPermitsResource(client)

    with pytest.raises(OilPriceAPIError, match="well_permits") as error:
        await resource.search(states="TX")

    assert error.value.code == "MALFORMED_RESPONSE"
