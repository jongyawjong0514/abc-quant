"""Market data validation utilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final
import warnings

import pandas as pd

from abc_quant.data.schema import (
    CLOSE_COLUMN,
    DATE_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    MARKET_NUMERIC_COLUMNS,
    MARKET_REQUIRED_COLUMNS,
    OPEN_COLUMN,
    TICKER_COLUMN,
    VOLUME_COLUMN,
)

REQUIRED_MARKET_COLUMNS: Final[frozenset[str]] = frozenset(MARKET_REQUIRED_COLUMNS)


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
            validated[DATE_COLUMN] = pd.to_datetime(validated[DATE_COLUMN], errors="raise")
    except (TypeError, ValueError) as exc:
        raise MarketDataValidationError("market data date column is not sortable") from exc

    if validated[DATE_COLUMN].isna().any():
        raise MarketDataValidationError("market data date column contains missing values")
    if validated[TICKER_COLUMN].isna().any():
        raise MarketDataValidationError("market data ticker column contains missing values")

    validated[TICKER_COLUMN] = validated[TICKER_COLUMN].astype("string")

    _normalize_numeric_columns(validated)
    _validate_ohlcv_values(validated)

    duplicate_mask = validated.duplicated(subset=[DATE_COLUMN, TICKER_COLUMN], keep=False)
    if duplicate_mask.any():
        examples = validated.loc[duplicate_mask, [DATE_COLUMN, TICKER_COLUMN]].head(5)
        raise MarketDataValidationError(
            "market data contains duplicate date+ticker rows: "
            + examples.to_dict(orient="records").__repr__()
        )

    if sort:
        validated = validated.sort_values([TICKER_COLUMN, DATE_COLUMN]).reset_index(drop=True)
    return validated


def _normalize_numeric_columns(data: pd.DataFrame) -> None:
    for column in MARKET_NUMERIC_COLUMNS:
        try:
            data[column] = pd.to_numeric(data[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise MarketDataValidationError(
                f"market data numeric column is not numeric: {column}"
            ) from exc

    missing_columns = [
        column for column in MARKET_NUMERIC_COLUMNS if data[column].isna().any()
    ]
    if missing_columns:
        raise MarketDataValidationError(
            "market data numeric columns contain missing values: "
            + ", ".join(missing_columns)
        )


def _validate_ohlcv_values(data: pd.DataFrame) -> None:
    _raise_for_rows(
        data,
        data[VOLUME_COLUMN] < 0,
        "market data volume column contains negative values",
    )
    _raise_for_rows(
        data,
        data[HIGH_COLUMN] < data[LOW_COLUMN],
        "market data high column is lower than low column",
    )
    _raise_for_rows(
        data,
        (data[OPEN_COLUMN] < data[LOW_COLUMN]) | (data[OPEN_COLUMN] > data[HIGH_COLUMN]),
        "market data open column is outside the high-low range",
    )
    _raise_for_rows(
        data,
        (data[CLOSE_COLUMN] < data[LOW_COLUMN]) | (data[CLOSE_COLUMN] > data[HIGH_COLUMN]),
        "market data close column is outside the high-low range",
    )


def _raise_for_rows(data: pd.DataFrame, mask: pd.Series, message: str) -> None:
    if not mask.any():
        return
    examples = data.loc[mask, [DATE_COLUMN, TICKER_COLUMN]].head(5)
    raise MarketDataValidationError(
        message + ": " + examples.to_dict(orient="records").__repr__()
    )
