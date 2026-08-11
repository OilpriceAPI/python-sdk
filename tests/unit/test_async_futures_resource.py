"""Async futures routes use instrument-generic API paths."""

from unittest.mock import AsyncMock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI


@pytest.fixture
def client():
    return AsyncOilPriceAPI(api_key="test_key")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["latest", "historical", "ohlc", "intraday", "curve"]
)
@pytest.mark.parametrize(
    "contract,canonical",
    [
        ("brent", "brent"),
        ("BZ", "brent"),
        ("ice-brent", "brent"),
        ("wti", "wti"),
        ("CL", "wti"),
        ("ice-wti", "wti"),
        ("gasoil", "gasoil"),
        ("G", "gasoil"),
        ("ice-gasoil", "gasoil"),
        ("eu-carbon", "eu-carbon"),
        ("EUA", "eu-carbon"),
        ("eua-carbon", "eu-carbon"),
    ],
)
async def test_futures_methods_use_generic_routes(
    client, method, contract, canonical
):
    suffix = "" if method == "latest" else f"/{method}"
    request = AsyncMock(return_value={"data": []})
    with patch.object(client, "request", new=request):
        await getattr(client.futures, method)(contract)

    assert request.call_args.kwargs["path"] == f"/v1/futures/{canonical}{suffix}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contract,canonical",
    [
        ("brent", "brent"),
        ("BZ", "brent"),
        ("ice-brent", "brent"),
        ("wti", "wti"),
        ("CL", "wti"),
        ("ice-wti", "wti"),
    ],
)
async def test_continuous_accepts_generic_code_and_legacy_inputs(
    client, contract, canonical
):
    request = AsyncMock(return_value={"data": []})
    with patch.object(client, "request", new=request):
        await client.futures.continuous(contract)

    assert request.call_args.kwargs["path"] == (
        f"/v1/futures/continuous/{canonical}/historical"
    )
