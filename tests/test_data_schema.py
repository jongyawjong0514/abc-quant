import pandas as pd

from abc_quant.data.sample import sample_market_data
from abc_quant.data.schema import (
    MARKET_DTYPE_INTENT,
    MARKET_NUMERIC_COLUMNS,
    MARKET_REQUIRED_COLUMNS,
)


def test_market_schema_declares_required_columns_and_dtype_intent() -> None:
    assert MARKET_REQUIRED_COLUMNS == (
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    assert MARKET_NUMERIC_COLUMNS == ("open", "high", "low", "close", "volume")
    assert MARKET_DTYPE_INTENT["date"] == "datetime64[ns]"
    assert MARKET_DTYPE_INTENT["ticker"] == "string"
    assert MARKET_DTYPE_INTENT["close"] == "float64"
    assert MARKET_DTYPE_INTENT["volume"] == "int64"


def test_sample_market_data_is_deterministic_multi_ticker_contract_fixture() -> None:
    first = sample_market_data()
    second = sample_market_data()

    pd.testing.assert_frame_equal(first, second)
    assert tuple(first.columns) == MARKET_REQUIRED_COLUMNS
    assert sorted(first["ticker"].unique()) == ["2317", "2330"]
    assert first.groupby("ticker").size().to_dict() == {"2317": 12, "2330": 12}
    assert first["date"].is_monotonic_increasing is False
