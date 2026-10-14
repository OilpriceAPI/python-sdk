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


# Simulates an install without matplotlib: a None entry in sys.modules makes
# ``import matplotlib`` raise ImportError in a fresh interpreter.
_NO_MPL = (
    "import sys; sys.modules['matplotlib'] = None; "
    "sys.modules['matplotlib.pyplot'] = None; "
)


@pytest.mark.parametrize(
    "call",
    [
        "c.viz.plot_price_series('WTI_USD')",
        "c.viz.plot_spread('BRENT_CRUDE_USD', 'WTI_USD')",
        "c.viz.create_sparkline([1.0, 2.0])",
        "c.viz.create_small_multiples(['WTI_USD'])",
    ],
)
def test_plotting_without_matplotlib_names_the_extra(call):
    # Review of #157: client.viz returned None without matplotlib, so every
    # documented ``client.viz.plot_*`` call died with a bare AttributeError.
    code = (
        _NO_MPL
        + "import oilpriceapi; c = oilpriceapi.OilPriceAPI(api_key='x')\n"
        + "try:\n"
        + f"    {call}\n"
        + "except ImportError as e:\n"
        + "    print('IMPORTERROR:' + str(e))\n"
        + "except Exception as e:\n"
        + "    print('OTHER:' + type(e).__name__ + ':' + str(e))\n"
        + "c.close()"
    )
    result = subprocess.run(
        [sys.executable, "-W", "error", "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout.strip()
    assert out.startswith("IMPORTERROR:"), out
    assert "pip install 'oilpriceapi[viz]'" in out, out


def test_construction_without_matplotlib_is_warning_free():
    code = _NO_MPL + "import oilpriceapi; oilpriceapi.OilPriceAPI(api_key='x').close()"
    result = subprocess.run(
        [sys.executable, "-W", "error", "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_viz_is_a_cached_visualizer():
    from oilpriceapi.visualization import PriceVisualizer

    client = OilPriceAPI(api_key="x")
    try:
        assert isinstance(client.viz, PriceVisualizer)
        assert client.viz is client.viz
    finally:
        client.close()
