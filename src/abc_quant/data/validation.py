"""Market data validation utilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final
import warnings

import pandas as pd

REQUIRED_MARKET_COLUMNS: Final[frozenset[str]] = frozenset(
    {"date", "ticker", "open", "high", "low", "close", "volume"}
)


class MarketDataValidationError(ValueError):
    """Raised when market data violate the project OHLCV contract."""


def required_market_columns() -> set[str]:
    """Return the standard required columns for daily OHLCV market data."""
    return set(REQUIRED_MARKET_COLUMNS)


def validate_market_data(
    data: pd.DataFrame,
    *,
    required_columns: Iterable[str] = REQUIRED_MARKET_COLUMNS,
    sort: bool = True,
) -> pd.DataFrame:
    """Validate daily OHLCV market data and return a defensive copy.

    The returned frame has a datetime-like ``date`` column and, by default, is
    sorted by ``ticker`` then ``date``. Sorting is a normalization step only;
    it never allows features or labels to read future rows.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("market data must be a pandas DataFrame")

    required = set(required_columns)
    missing = sorted(required.difference(data.columns))
    if missing:
        raise MarketDataValidationError(
            "market data missing required columns: " + ", ".join(missing)
        )

    validated = data.copy()
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Could not infer format",
                category=UserWarning,
            )
            validated["date"] = pd.to_datetime(validated["date"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise MarketDataValidationError("market data date column is not sortable") from exc

    if validated["date"].isna().any():
        raise MarketDataValidationError("market data date column contains missing values")
    if validated["ticker"].isna().any():
        raise MarketDataValidationError("market data ticker column contains missing values")

    duplicate_mask = validated.duplicated(subset=["date", "ticker"], keep=False)
    if duplicate_mask.any():
        examples = validated.loc[duplicate_mask, ["date", "ticker"]].head(5)
        raise MarketDataValidationError(
            "market data contains duplicate date+ticker rows: "
            + examples.to_dict(orient="records").__repr__()
        )

    if sort:
        validated = validated.sort_values(["ticker", "date"]).reset_index(drop=True)
    return validated
