import pandas as pd
import pytest

from abc_quant.labels.returns import add_forward_return_label
from test_helpers import _assert_same_by_date_ticker


def _multi_ticker_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    specs = {
        "2317": [50.0, 55.0, 60.0, 66.0, 72.0],
        "2330": [10.0, 11.0, 13.0, 17.0, 19.0],
    }
    for ticker, closes in specs.items():
        for index, date in enumerate(pd.date_range("2026-01-01", periods=5, freq="D")):
            close = closes[index]
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": close,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 100 + index,
                }
            )
    return pd.DataFrame(rows)


def test_forward_return_label_uses_next_period_entry() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "ticker": ["2330"] * 5,
            "open": [10.0, 11.0, 13.0, 17.0, 19.0],
            "high": [10.5, 11.5, 13.5, 17.5, 19.5],
            "low": [9.5, 10.5, 12.5, 16.5, 18.5],
            "close": [10.0, 11.0, 13.0, 17.0, 19.0],
            "volume": [100, 110, 120, 130, 140],
        }
    )

    labeled = add_forward_return_label(data, horizon=3, entry_lag=1)
    label_col = "label_forward_return_3d_entry_lag_1d"

    assert labeled.loc[0, label_col] == 17.0 / 11.0 - 1.0
    assert labeled.loc[1, label_col] == 19.0 / 13.0 - 1.0
    assert pd.isna(labeled.loc[2, label_col])


def test_forward_return_label_requires_exit_after_entry() -> None:
    data = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "ticker": ["2330", "2330"],
            "open": [10.0, 11.0],
            "high": [10.5, 11.5],
            "low": [9.5, 10.5],
            "close": [10.0, 11.0],
            "volume": [100, 110],
        }
    )

    with pytest.raises(ValueError, match="horizon must be greater than entry_lag"):
        add_forward_return_label(data, horizon=1, entry_lag=1)


def test_forward_return_label_is_isolated_by_ticker_and_has_missing_tail() -> None:
    labeled = add_forward_return_label(_multi_ticker_frame(), horizon=3, entry_lag=1)
    label_col = "label_forward_return_3d_entry_lag_1d"

    ticker_2317 = labeled[labeled["ticker"] == "2317"].reset_index(drop=True)
    ticker_2330 = labeled[labeled["ticker"] == "2330"].reset_index(drop=True)

    assert ticker_2317.loc[0, label_col] == pytest.approx(66.0 / 55.0 - 1.0)
    assert ticker_2317.loc[1, label_col] == pytest.approx(72.0 / 60.0 - 1.0)
    assert ticker_2330.loc[0, label_col] == pytest.approx(17.0 / 11.0 - 1.0)
    assert ticker_2330.loc[1, label_col] == pytest.approx(19.0 / 13.0 - 1.0)
    assert ticker_2317.loc[2:, label_col].isna().all()
    assert ticker_2330.loc[2:, label_col].isna().all()


def test_shuffled_input_produces_same_sorted_forward_return_labels() -> None:
    sorted_input = _multi_ticker_frame()
    shuffled_input = sorted_input.sample(frac=1.0, random_state=23).reset_index(drop=True)

    sorted_labeled = add_forward_return_label(sorted_input, horizon=3, entry_lag=1)
    shuffled_labeled = add_forward_return_label(shuffled_input, horizon=3, entry_lag=1)
    label_col = "label_forward_return_3d_entry_lag_1d"

    _assert_same_by_date_ticker(sorted_labeled, shuffled_labeled, [label_col])
