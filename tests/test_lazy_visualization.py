"""#151: constructing a client must not warn about optional matplotlib."""

import subprocess
import sys
import warnings

import pytest

from oilpriceapi import OilPriceAPI


def test_client_construction_emits_no_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        client = OilPriceAPI(api_key="x")
    client.close()


def test_import_and_construct_under_W_error():
    # The acceptance check from the issue, in a fresh interpreter so no
    # earlier import has already filtered or triggered the warning.
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            "import oilpriceapi; oilpriceapi.OilPriceAPI(api_key='x').close()",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_construction_does_not_import_matplotlib():
    code = (
        "import sys, oilpriceapi; c = oilpriceapi.OilPriceAPI(api_key='x'); "
        "print('matplotlib' in sys.modules); c.close()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_viz_is_none_without_matplotlib_and_object_with_it():
    client = OilPriceAPI(api_key="x")
    try:
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            assert client.viz is None
        else:
            from oilpriceapi.visualization import PriceVisualizer

            assert isinstance(client.viz, PriceVisualizer)
            assert client.viz is client.viz
    finally:
        client.close()
