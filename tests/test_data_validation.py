import pandas as pd
import pytest

from abc_quant.data.validation import MarketDataValidationError, validate_market_data


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


def test_validate_market_data_normalizes_sortable_dates() -> None:
    validated = validate_market_data(_market_frame())

    assert list(validated[["ticker", "date"]].itertuples(index=False, name=None)) == [
        ("2317", pd.Timestamp("2026-01-01")),
        ("2330", pd.Timestamp("2026-01-01")),
        ("2330", pd.Timestamp("2026-01-02")),
    ]


def test_validate_market_data_rejects_duplicate_date_ticker() -> None:
    data = pd.concat([_market_frame(), _market_frame().iloc[[0]]], ignore_index=True)

    with pytest.raises(MarketDataValidationError, match="duplicate date\\+ticker"):
        validate_market_data(data)


def test_validate_market_data_rejects_unsortable_date() -> None:
    data = _market_frame()
    data.loc[0, "date"] = "not-a-date"

    with pytest.raises(MarketDataValidationError, match="date column is not sortable"):
        validate_market_data(data)
