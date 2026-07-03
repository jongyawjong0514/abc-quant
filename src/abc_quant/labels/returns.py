"""Forward return label generation."""

from __future__ import annotations

import pandas as pd

from abc_quant.data.validation import validate_market_data


def add_forward_return_label(
    market_data: pd.DataFrame,
    *,
    horizon: int = 20,
    entry_lag: int = 1,
    price_col: str = "close",
    label_col: str | None = None,
) -> pd.DataFrame:
    """Add a forward return label with an explicit next-period entry rule.

    Time definition for row ``t``:

    ``entry_price = close[t + entry_lag]``
    ``exit_price = close[t + horizon]``
    ``label = exit_price / entry_price - 1``

    With the default ``entry_lag=1``, a decision made after date ``t`` close is
    assumed to enter from the next available bar. This avoids the invalid
    assumption that a same-day close decision can also trade at that same close.
    Labels are evaluator-only targets and must not be used as input features.
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if entry_lag < 0:
        raise ValueError("entry_lag must be zero or positive")
    if horizon <= entry_lag:
        raise ValueError("horizon must be greater than entry_lag")

    data = validate_market_data(market_data)
    if price_col not in data.columns:
        raise KeyError(f"price column not found: {price_col}")

    output_col = label_col or f"label_forward_return_{horizon}d_entry_lag_{entry_lag}d"
    grouped = data.groupby("ticker", group_keys=False, sort=False)[price_col]
    entry_price = grouped.shift(-entry_lag)
    exit_price = grouped.shift(-horizon)
    data[output_col] = (exit_price / entry_price) - 1.0
    return data
