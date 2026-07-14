import pandas as pd
import pytest

from scripts.analyze_zhu_walkline_kd_d5_groups import (
    apply_same_stock_cooldown,
    assign_d5_group,
    attach_d5_labels,
    compute_pairwise_numeric_contrasts,
)


def test_assign_d5_group_uses_mutually_exclusive_boundaries() -> None:
    assert assign_d5_group(-0.01) == "D5_LOSS"
    assert assign_d5_group(0.0) == ""
    assert assign_d5_group(9.999) == ""
    assert assign_d5_group(10.0) == "D5_GAIN_10_20"
    assert assign_d5_group(19.999) == "D5_GAIN_10_20"
    assert assign_d5_group(20.0) == "D5_GAIN_GE_20"
    assert assign_d5_group(((120.0 / 100.0) - 1.0) * 100.0) == "D5_GAIN_GE_20"


def test_attach_d5_labels_uses_fifth_future_trading_close_only() -> None:
    events = pd.DataFrame(
        [{"asof_date": "2026-01-02", "stock_id": "2330", "close": 100.0}]
    )
    prices = _price_rows("2330", [100.0, 102.0, 104.0, 106.0, 110.0, 115.0, 999.0])

    labeled = attach_d5_labels(events, adjusted_prices=prices, horizon_trading_days=5)
    row = labeled.iloc[0]

    assert row["d5_close_date"] == "2026-01-09"
    assert row["d5_adj_close"] == 115.0
    assert row["d5_adjusted_return_pct"] == pytest.approx(15.0)
    assert bool(row["label_mature"])


def test_future_day_six_mutation_does_not_change_d5_label() -> None:
    events = pd.DataFrame(
        [{"asof_date": "2026-01-02", "stock_id": "2330", "close": 100.0}]
    )
    baseline = _price_rows("2330", [100.0, 102.0, 104.0, 106.0, 110.0, 115.0, 116.0])
    mutated = baseline.copy()
    mutated.loc[6, ["close", "adj_close"]] = 9999.0

    baseline_row = attach_d5_labels(
        events, adjusted_prices=baseline, horizon_trading_days=5
    ).iloc[0]
    mutated_row = attach_d5_labels(
        events, adjusted_prices=mutated, horizon_trading_days=5
    ).iloc[0]

    assert mutated_row["d5_close_date"] == baseline_row["d5_close_date"]
    assert mutated_row["d5_adjusted_return_pct"] == baseline_row["d5_adjusted_return_pct"]


def test_attach_d5_labels_flags_adjustment_factor_change() -> None:
    events = pd.DataFrame(
        [{"asof_date": "2026-01-02", "stock_id": "2330", "close": 100.0}]
    )
    prices = _price_rows("2330", [100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    prices.loc[5, "adjustment_factor"] = 0.9

    row = attach_d5_labels(events, adjusted_prices=prices, horizon_trading_days=5).iloc[0]

    assert bool(row["corporate_action_event_in_horizon"])


def test_same_stock_cooldown_removes_overlapping_five_day_signals() -> None:
    rows = pd.DataFrame(
        {
            "stock_id": ["2330", "2330", "2330", "2317"],
            "asof_date": ["2026-01-02", "2026-01-05", "2026-01-12", "2026-01-05"],
            "signal_trade_index": [0, 1, 6, 1],
        }
    )

    selected = apply_same_stock_cooldown(rows, horizon_trading_days=5)

    assert selected[selected["stock_id"].eq("2330")]["signal_trade_index"].tolist() == [0, 6]
    assert selected[selected["stock_id"].eq("2317")]["signal_trade_index"].tolist() == [1]


def test_pairwise_numeric_contrast_compares_gain_groups_with_loss() -> None:
    rows = pd.DataFrame(
        {
            "d5_group": [
                "D5_LOSS",
                "D5_LOSS",
                "D5_GAIN_10_20",
                "D5_GAIN_10_20",
                "D5_GAIN_GE_20",
                "D5_GAIN_GE_20",
            ],
            "d5_group_label": [
                "5日後低於訊號日",
                "5日後低於訊號日",
                "5日後上漲10%至未滿20%",
                "5日後上漲10%至未滿20%",
                "5日後上漲20%或以上",
                "5日後上漲20%或以上",
            ],
            "kd_k9": [30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
        }
    )

    contrasts = compute_pairwise_numeric_contrasts(rows, scope="test")
    kd_rows = contrasts[contrasts["feature"].eq("kd_k9")].set_index("target_group")

    assert kd_rows.loc["D5_GAIN_10_20", "mean_difference"] == pytest.approx(20.0)
    assert kd_rows.loc["D5_GAIN_GE_20", "mean_difference"] == pytest.approx(40.0)
    assert (kd_rows["standardized_mean_difference"] > 0).all()


def _price_rows(stock_id: str, closes: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-02", periods=len(closes))
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": stock_id,
            "close": closes,
            "adj_close": closes,
            "adjustment_factor": [1.0] * len(closes),
            "factor_event_count": [0] * len(closes),
            "adjusted_data_asof": ["2026-07-09"] * len(closes),
        }
    )
