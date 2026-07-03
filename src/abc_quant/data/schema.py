"""Market data schema constants for deterministic local checks."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

DATE_COLUMN: Final[str] = "date"
TICKER_COLUMN: Final[str] = "ticker"
OPEN_COLUMN: Final[str] = "open"
HIGH_COLUMN: Final[str] = "high"
LOW_COLUMN: Final[str] = "low"
CLOSE_COLUMN: Final[str] = "close"
VOLUME_COLUMN: Final[str] = "volume"

MARKET_REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    DATE_COLUMN,
    TICKER_COLUMN,
    OPEN_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    CLOSE_COLUMN,
    VOLUME_COLUMN,
)

MARKET_NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    OPEN_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    CLOSE_COLUMN,
    VOLUME_COLUMN,
)

MARKET_DTYPE_INTENT: Final[Mapping[str, str]] = MappingProxyType(
    {
        DATE_COLUMN: "datetime64[ns]",
        TICKER_COLUMN: "string",
        OPEN_COLUMN: "float64",
        HIGH_COLUMN: "float64",
        LOW_COLUMN: "float64",
        CLOSE_COLUMN: "float64",
        VOLUME_COLUMN: "int64",
    }
)
