"""Technical indicator feature engineering."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from abc_quant.data.validation import validate_market_data


def add_technical_indicators(
    market_data: pd.DataFrame,
    *,
    sma_windows: Sequence[int] = (5, 20, 60),
    ema_spans: Sequence[int] = (12, 26),
    rsi_windows: Sequence[int] = (14,),
    price_col: str = "close",
) -> pd.DataFrame:
    """Add no-lookahead SMA, EMA, and RSI features.

    For each ticker, every value at date ``t`` uses only that ticker's price
    values at or before ``t``. Input rows are validated and sorted before group
    operations so shuffled input cannot change the resulting feature values.
    """
    data = validate_market_data(market_data)
    if price_col not in data.columns:
        raise KeyError(f"price column not found: {price_col}")

    grouped = data.groupby("ticker", group_keys=False, sort=False)

    for window in _validate_positive_ints(sma_windows, "sma_windows"):
        data[f"sma_{window}d"] = grouped[price_col].transform(
            lambda series, rolling_window=window: series.rolling(
                window=rolling_window,
                min_periods=rolling_window,
            ).mean()
        )

    for span in _validate_positive_ints(ema_spans, "ema_spans"):
        data[f"ema_{span}d"] = grouped[price_col].transform(
            lambda series, ema_span=span: series.ewm(
                span=ema_span,
                adjust=False,
                min_periods=ema_span,
            ).mean()
        )

    for window in _validate_positive_ints(rsi_windows, "rsi_windows"):
        data[f"rsi_{window}d"] = grouped[price_col].transform(
            lambda series, rsi_window=window: _rsi(series, rsi_window)
        )

    return data


def _validate_positive_ints(values: Sequence[int], name: str) -> tuple[int, ...]:
    normalized = tuple(int(value) for value in values)
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    invalid = [value for value in normalized if value <= 0]
    if invalid:
        raise ValueError(f"{name} must contain positive integers: {invalid}")
    return normalized


def _rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    average_gain = gain.rolling(window=window, min_periods=window).mean()
    average_loss = loss.rolling(window=window, min_periods=window).mean()
    relative_strength = average_gain / average_loss
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))

    rsi = rsi.mask((average_loss == 0.0) & (average_gain > 0.0), 100.0)
    rsi = rsi.mask((average_loss == 0.0) & (average_gain == 0.0), 50.0)
    return rsi
