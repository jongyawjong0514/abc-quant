import pandas as pd
import pytest

from abc_quant.data.schema import MARKET_REQUIRED_COLUMNS
from abc_quant.data.validation import (
    MarketDataValidationError,
    required_market_columns,
    validate_market_data,
)


def _market_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-01-02", "2026-01-01", "2026-01-01"],
            "ticker": ["2330", "2330", "2317"],
            "open": [101.0, 100.0, 50.0],
            "high": [103.0, 102.0, 51.0],
            "low": [100.0, 99.0, 49.0],
            "close": [102.0, 101.0, 50.5],
            "volume": [1000, 900, 2000],
        }
    )


def test_validate_market_data_requires_standard_columns() -> None:
    data = _market_frame().drop(columns=["volume"])

    with pytest.raises(MarketDataValidationError, match="missing required columns: volume"):
        validate_market_data(data)


def test_required_market_columns_uses_schema_contract() -> None:
    assert required_market_columns() == set(MARKET_REQUIRED_COLUMNS)


def test_validate_market_data_normalizes_sortable_dates() -> None:
    validated = validate_market_data(_market_frame())

    assert list(validated[["ticker", "date"]].itertuples(index=False, name=None)) == [
        ("2317", pd.Timestamp("2026-01-01")),
        ("2330", pd.Timestamp("2026-01-01")),
        ("2330", pd.Timestamp("2026-01-02")),
    ]
    assert str(validated["ticker"].dtype) == "string"


def test_validate_market_data_converts_ticker_values_to_string() -> None:
    data = _market_frame()
    data["ticker"] = [2330, 2330, 2317]

    validated = validate_market_data(data)

    assert list(validated["ticker"]) == ["2317", "2330", "2330"]
    assert str(validated["ticker"].dtype) == "string"


def test_validate_market_data_rejects_duplicate_date_ticker() -> None:
    data = pd.concat([_market_frame(), _market_frame().iloc[[0]]], ignore_index=True)

    with pytest.raises(MarketDataValidationError, match="duplicate date\\+ticker"):
        validate_market_data(data)


def test_validate_market_data_rejects_unsortable_date() -> None:
    data = _market_frame()
    data.loc[0, "date"] = "not-a-date"

    with pytest.raises(MarketDataValidationError, match="date column is not sortable"):
        validate_market_data(data)


@pytest.mark.parametrize("column", ["open", "high", "low", "close", "volume"])
def test_validate_market_data_rejects_non_numeric_ohlcv_values(column: str) -> None:
    data = _market_frame()
    data[column] = data[column].astype("object")
    data.loc[0, column] = "not-numeric"

    with pytest.raises(
        MarketDataValidationError,
        match=f"numeric column is not numeric: {column}",
    ):
        validate_market_data(data)


@pytest.mark.parametrize("column", ["open", "high", "low", "close", "volume"])
def test_validate_market_data_rejects_missing_ohlcv_values(column: str) -> None:
    data = _market_frame()
    data.loc[0, column] = None

    with pytest.raises(
        MarketDataValidationError,
        match=f"numeric columns contain missing values: {column}",
    ):
        validate_market_data(data)


def test_validate_market_data_rejects_negative_volume() -> None:
    data = _market_frame()
    data.loc[0, "volume"] = -1

    with pytest.raises(MarketDataValidationError, match="volume column contains negative"):
        validate_market_data(data)


def test_validate_market_data_rejects_high_lower_than_low() -> None:
    data = _market_frame()
    data.loc[0, "high"] = 99.0

    with pytest.raises(MarketDataValidationError, match="high column is lower than low"):
        validate_market_data(data)


def test_validate_market_data_rejects_open_outside_high_low_range() -> None:
    data = _market_frame()
    data.loc[0, "open"] = 99.0

    with pytest.raises(MarketDataValidationError, match="open column is outside"):
        validate_market_data(data)


def test_validate_market_data_rejects_close_outside_high_low_range() -> None:
    data = _market_frame()
    data.loc[0, "close"] = 99.0

    with pytest.raises(MarketDataValidationError, match="close column is outside"):
        validate_market_data(data)
