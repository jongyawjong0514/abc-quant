import pandas as pd
import pytest

from abc_quant.labels.returns import add_forward_return_label


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
