"""Price and volume feature engineering."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from abc_quant.data.validation import validate_market_data


def add_price_volume_features(
    market_data: pd.DataFrame,
    *,
    momentum_windows: Sequence[int] = (5, 20, 60),
    volatility_windows: Sequence[int] = (10, 20),
    volume_windows: Sequence[int] = (5, 20),
    price_col: str = "close",
    volume_col: str = "volume",
) -> pd.DataFrame:
    """Add no-lookahead rolling price and volume features.

    For each ticker, every rolling feature at date ``t`` uses only values at or
    before ``t``. The function validates and sorts data before computing group
    operations so shuffled input rows cannot accidentally leak future values.
    """
    data = validate_market_data(market_data)
    if price_col not in data.columns:
        raise KeyError(f"price column not found: {price_col}")
    if volume_col not in data.columns:
        raise KeyError(f"volume column not found: {volume_col}")

    grouped = data.groupby("ticker", group_keys=False, sort=False)

    for window in _validate_windows(momentum_windows, "momentum_windows"):
        data[f"price_momentum_{window}d"] = grouped[price_col].pct_change(periods=window)

    returns = grouped[price_col].pct_change()
    for window in _validate_windows(volatility_windows, "volatility_windows"):
        data[f"price_volatility_{window}d"] = (
            returns.groupby(data["ticker"], group_keys=False)
            .rolling(window=window, min_periods=window)
            .std(ddof=0)
            .reset_index(level=0, drop=True)
        )

    for window in _validate_windows(volume_windows, "volume_windows"):
        data[f"volume_average_{window}d"] = grouped[volume_col].transform(
            lambda series, rolling_window=window: series.rolling(
                window=rolling_window, min_periods=rolling_window
            ).mean()
        )

    return data


def _validate_windows(windows: Sequence[int], name: str) -> tuple[int, ...]:
    normalized = tuple(int(window) for window in windows)
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    invalid = [window for window in normalized if window <= 0]
    if invalid:
        raise ValueError(f"{name} must contain positive integers: {invalid}")
    return normalized
