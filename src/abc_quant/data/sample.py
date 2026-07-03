"""Deterministic in-memory market data fixtures."""

from __future__ import annotations

import pandas as pd

from abc_quant.data.schema import (
    CLOSE_COLUMN,
    DATE_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    OPEN_COLUMN,
    TICKER_COLUMN,
    VOLUME_COLUMN,
)


def sample_market_data() -> pd.DataFrame:
    """Return a deterministic multi-ticker OHLCV fixture for smoke tests.

    The fixture is intentionally tiny and synthetic. It is useful only for
    contract and pipeline smoke checks, not for trading research conclusions.
    """
    dates = pd.date_range("2026-01-02", periods=12, freq="B")
    ticker_specs = (
        ("2317", 50.0, 0.65, 1_200),
        ("2330", 100.0, 1.10, 2_400),
    )

    rows: list[dict[str, object]] = []
    for ticker, base_close, daily_step, base_volume in ticker_specs:
        for index, date in enumerate(dates):
            close = base_close + daily_step * index + (0.15 if index % 3 == 0 else -0.05)
            open_price = close - 0.20 + (0.05 if index % 2 == 0 else -0.05)
            rows.append(
                {
                    DATE_COLUMN: date,
                    TICKER_COLUMN: ticker,
                    OPEN_COLUMN: round(open_price, 4),
                    HIGH_COLUMN: round(max(open_price, close) + 0.45, 4),
                    LOW_COLUMN: round(min(open_price, close) - 0.45, 4),
                    CLOSE_COLUMN: round(close, 4),
                    VOLUME_COLUMN: base_volume + index * 25,
                }
            )

    return pd.DataFrame(rows)
