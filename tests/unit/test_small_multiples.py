"""#158: create_small_multiples crashed whenever every commodity fit in one row."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("matplotlib")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from oilpriceapi.visualization import PriceVisualizer  # noqa: E402


def _client():
    start = datetime(2026, 9, 1)
    points = [
        SimpleNamespace(date=start + timedelta(days=i), value=70.0 + i * 0.1)
        for i in range(60)
    ]
    client = MagicMock()
    client.historical.get.return_value = SimpleNamespace(data=points)
    return client


@pytest.mark.parametrize(
    "n,cols",
    [(1, 3), (2, 3), (3, 3), (4, 3), (6, 3), (2, 1), (1, 1), (5, 2)],
)
def test_small_multiples_any_shape(n, cols):
    codes = [f"C{i}" for i in range(n)]
    fig = PriceVisualizer(_client()).create_small_multiples(codes, cols=cols)
    try:
        titled = [ax.get_title() for ax in fig.axes if ax.get_title()]
        assert titled == codes
    finally:
        plt.close(fig)
