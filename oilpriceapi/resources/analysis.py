"""
Analysis Resource

Technical analysis indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR).

Implemented from scratch on top of pandas/numpy so the SDK gains no new
hard dependencies. All indicator math lives in this module; pandas is only
required at call time (the optional ``[pandas]`` extra), mirroring the rest
of the DataFrame-aware SDK surface.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd


_PANDAS_ERROR = (
    "pandas is required for technical indicators. "
    "Install with: pip install oilpriceapi[pandas]"
)


def _require_pandas() -> Any:
    """Import pandas lazily, raising a friendly error when it is missing."""
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(_PANDAS_ERROR)
    if pd is None:  # monkeypatched-out in tests / partial environments
        raise ImportError(_PANDAS_ERROR)
    return pd


class AnalysisResource:
    """Resource for technical analysis indicators.

    Two usage styles are supported (see GitHub issue #3):

    DataFrame helper::

        df = client.analysis.with_indicators(df, indicators=["sma_20", "rsi"])

    Direct calculation::

        df["sma_20"] = client.analysis.sma(df["value"], period=20)
        df["rsi"] = client.analysis.rsi(df["value"], period=14)
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        """Initialize analysis resource.

        Args:
            client: OilPriceAPI client instance (unused today, kept for
                parity with every other resource and future server-side
                indicator support).
        """
        self.client = client

    # ------------------------------------------------------------------
    # Direct indicators (Method 2)
    # ------------------------------------------------------------------
    def sma(self, series: "pd.Series", period: int = 20) -> "pd.Series":
        """Simple Moving Average over ``period`` observations."""
        _require_pandas()
        self._validate_period(period)
        return series.rolling(window=period).mean()

    def ema(self, series: "pd.Series", period: int = 20) -> "pd.Series":
        """Exponential Moving Average (span = ``period``)."""
        _require_pandas()
        self._validate_period(period)
        return series.ewm(span=period, adjust=False).mean()

    def rsi(self, series: "pd.Series", period: int = 14) -> "pd.Series":
        """Relative Strength Index using Wilder-style smoothing.

        Returns values in the ``[0, 100]`` range. When there are no losses
        in the smoothing window the RSI is pinned to ``100`` (and to ``0``
        when there are no gains), matching the standard definition.
        """
        pd = _require_pandas()
        self._validate_period(period)

        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # avg_loss == 0 -> rs == inf -> rsi already 100; guard NaN from 0/0.
        rsi = rsi.where(avg_loss != 0, 100.0)
        rsi = rsi.where(avg_gain != 0, 0.0)
        # Re-mask the warm-up period that has no defined average yet.
        warmup = avg_gain.isna() | avg_loss.isna()
        rsi = rsi.mask(warmup, pd.NA).astype("float64")
        return rsi

    def macd(
        self,
        series: "pd.Series",
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> "pd.DataFrame":
        """Moving Average Convergence Divergence.

        Returns a DataFrame with ``macd``, ``macd_signal`` and
        ``macd_histogram`` columns.
        """
        pd = _require_pandas()
        for value in (fast, slow, signal):
            self._validate_period(value)
        if fast >= slow:
            raise ValueError("MACD fast period must be smaller than slow period")

        fast_ema = series.ewm(span=fast, adjust=False).mean()
        slow_ema = series.ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame(
            {
                "macd": macd_line,
                "macd_signal": signal_line,
                "macd_histogram": histogram,
            }
        )

    def bollinger_bands(
        self,
        series: "pd.Series",
        period: int = 20,
        std: float = 2.0,
    ) -> "pd.DataFrame":
        """Bollinger Bands.

        Returns a DataFrame with ``bb_upper``, ``bb_middle`` and
        ``bb_lower`` columns. The middle band is the SMA; the outer bands
        are ``std`` rolling standard deviations away.
        """
        pd = _require_pandas()
        self._validate_period(period)
        if std <= 0:
            raise ValueError("std must be positive")

        middle = series.rolling(window=period).mean()
        deviation = series.rolling(window=period).std(ddof=0)
        upper = middle + std * deviation
        lower = middle - std * deviation
        return pd.DataFrame(
            {
                "bb_upper": upper,
                "bb_middle": middle,
                "bb_lower": lower,
            }
        )

    def atr(
        self,
        high: "pd.Series",
        low: "pd.Series",
        close: "pd.Series",
        period: int = 14,
    ) -> "pd.Series":
        """Average True Range from high/low/close series."""
        pd = _require_pandas()
        self._validate_period(period)

        prev_close = close.shift(1)
        true_range = pd.concat(
            [
                (high - low),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    # ------------------------------------------------------------------
    # DataFrame helper (Method 1)
    # ------------------------------------------------------------------
    def with_indicators(
        self,
        df: "pd.DataFrame",
        indicators: List[str],
        column: str = "value",
    ) -> "pd.DataFrame":
        """Return a copy of ``df`` with the requested indicator columns added.

        The input DataFrame is never mutated.

        Args:
            df: DataFrame containing a price column (default ``"value"``,
                matching ``client.prices.to_dataframe`` output).
            indicators: Indicator names to add. Supported tokens:

                * ``sma_<n>`` / ``ema_<n>`` - moving averages of period n
                * ``sma`` / ``ema`` - default period (20)
                * ``rsi`` / ``rsi_<n>`` - Relative Strength Index
                * ``bollinger_bands`` / ``bb`` - adds bb_upper/middle/lower
                * ``macd`` - adds macd/macd_signal/macd_histogram

            column: Name of the price column to compute indicators on.

        Returns:
            New DataFrame with indicator columns appended.

        Raises:
            ImportError: if pandas is not installed.
            KeyError: if ``column`` is not present in ``df``.
            ValueError: if an indicator token is not recognized.
        """
        _require_pandas()

        if column not in df.columns:
            raise KeyError(
                f"column {column!r} not found in DataFrame; "
                f"available columns: {list(df.columns)}"
            )

        out = df.copy()
        prices = out[column]

        for indicator in indicators:
            name = indicator.strip().lower()

            if name in ("bollinger_bands", "bollinger", "bb"):
                bands = self.bollinger_bands(prices)
                for col in bands.columns:
                    out[col] = bands[col]
            elif name == "macd":
                macd_df = self.macd(prices)
                for col in macd_df.columns:
                    out[col] = macd_df[col]
            elif name in ("rsi",) or name.startswith("rsi_"):
                period = self._parse_period(name, default=14)
                out[indicator] = self.rsi(prices, period=period)
            elif name == "sma" or name.startswith("sma_"):
                period = self._parse_period(name, default=20)
                out[indicator] = self.sma(prices, period=period)
            elif name == "ema" or name.startswith("ema_"):
                period = self._parse_period(name, default=20)
                out[indicator] = self.ema(prices, period=period)
            else:
                raise ValueError(
                    f"Unknown indicator: {indicator!r}. Supported: sma_<n>, "
                    "ema_<n>, rsi, rsi_<n>, bollinger_bands, macd"
                )

        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_period(period: int) -> None:
        if not isinstance(period, int) or period < 1:
            raise ValueError(f"period must be a positive integer, got {period!r}")

    @staticmethod
    def _parse_period(name: str, default: int) -> int:
        """Extract the trailing ``_<n>`` period from an indicator token."""
        if "_" not in name:
            return default
        suffix = name.rsplit("_", 1)[1]
        try:
            return int(suffix)
        except ValueError:
            raise ValueError(f"Invalid period in indicator: {name!r}")
