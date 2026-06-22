"""
Unit tests for AnalysisResource (technical indicators).

Covers GitHub issue #3: Technical Indicators Module.

These tests require pandas/numpy and are skipped automatically when the
optional ``[pandas]`` extra is not installed (mirrors the existing
``test_historical_resource.py`` pattern).
"""

import sys

import pytest

from oilpriceapi import OilPriceAPI

pd = pytest.importorskip("pandas")


@pytest.fixture
def client():
    """Create a test client."""
    return OilPriceAPI(api_key="test_key")


@pytest.fixture
def price_series():
    """A deterministic, gently trending price series for indicator math."""
    values = [
        100, 101, 102, 101, 103, 104, 105, 104, 106, 107,
        108, 109, 110, 109, 111, 112, 113, 112, 114, 115,
        116, 117, 118, 117, 119, 120, 121, 120, 122, 123,
    ]
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype="float64", name="value")


@pytest.fixture
def price_df(price_series):
    """DataFrame shaped like ``client.prices.to_dataframe`` output."""
    return pd.DataFrame({"value": price_series})


class TestAnalysisResourceWiring:
    """The resource must be wired onto the client like every other resource."""

    def test_client_exposes_analysis_resource(self, client):
        assert hasattr(client, "analysis")
        assert client.analysis is not None


class TestDirectIndicators:
    """Method 2 from the issue: direct calculation on a Series."""

    def test_sma_matches_pandas_rolling_mean(self, client, price_series):
        result = client.analysis.sma(price_series, period=20)
        expected = price_series.rolling(window=20).mean()
        pd.testing.assert_series_equal(result, expected, check_names=False)
        assert result.isna().sum() == 19
        assert not pd.isna(result.iloc[19])

    def test_ema_matches_pandas_ewm(self, client, price_series):
        result = client.analysis.ema(price_series, period=10)
        expected = price_series.ewm(span=10, adjust=False).mean()
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_rsi_bounded_0_to_100(self, client, price_series):
        result = client.analysis.rsi(price_series, period=14)
        defined = result.dropna()
        assert len(defined) > 0
        assert (defined >= 0).all()
        assert (defined <= 100).all()

    def test_rsi_all_gains_is_100(self, client):
        rising = pd.Series([float(i) for i in range(1, 30)])
        result = client.analysis.rsi(rising, period=14)
        assert result.dropna().iloc[-1] == pytest.approx(100.0)

    def test_bollinger_bands_returns_three_bands(self, client, price_series):
        bands = client.analysis.bollinger_bands(price_series, period=20, std=2)
        assert set(["bb_upper", "bb_middle", "bb_lower"]).issubset(bands.columns)
        valid = bands.dropna()
        assert len(valid) > 0
        assert (valid["bb_upper"] >= valid["bb_middle"]).all()
        assert (valid["bb_middle"] >= valid["bb_lower"]).all()
        sma = price_series.rolling(window=20).mean()
        pd.testing.assert_series_equal(
            bands["bb_middle"], sma, check_names=False
        )


class TestWithIndicators:
    """Method 1 from the issue: DataFrame helper."""

    def test_with_indicators_is_non_mutating(self, client, price_df):
        before = price_df.copy()
        client.analysis.with_indicators(price_df, indicators=["sma_20"])
        pd.testing.assert_frame_equal(price_df, before)

    def test_with_indicators_adds_requested_columns(self, client, price_df):
        out = client.analysis.with_indicators(
            price_df,
            indicators=["sma_20", "sma_50", "rsi", "bollinger_bands", "macd"],
        )
        for col in ["sma_20", "sma_50", "rsi", "bb_upper", "bb_middle", "bb_lower"]:
            assert col in out.columns, f"missing column {col}"
        assert "macd" in out.columns
        assert "macd_signal" in out.columns

    def test_with_indicators_sma_values_correct(self, client, price_df):
        out = client.analysis.with_indicators(price_df, indicators=["sma_20"])
        expected = price_df["value"].rolling(window=20).mean()
        pd.testing.assert_series_equal(
            out["sma_20"], expected, check_names=False
        )

    def test_with_indicators_unknown_indicator_raises(self, client, price_df):
        with pytest.raises(ValueError):
            client.analysis.with_indicators(price_df, indicators=["not_real"])

    def test_with_indicators_custom_value_column(self, client, price_series):
        df = pd.DataFrame({"price": price_series})
        out = client.analysis.with_indicators(
            df, indicators=["sma_20"], column="price"
        )
        assert "sma_20" in out.columns


class TestPandasGuard:
    """The optional-dependency guard mirrors the rest of the SDK."""

    def test_with_indicators_without_pandas_raises_importerror(
        self, client, price_df, monkeypatch
    ):
        monkeypatch.setitem(sys.modules, "pandas", None)
        with pytest.raises(ImportError) as exc_info:
            client.analysis.with_indicators(price_df, indicators=["sma_20"])
        assert "pandas is required" in str(exc_info.value)
