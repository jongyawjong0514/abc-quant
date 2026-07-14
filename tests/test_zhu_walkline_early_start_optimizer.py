import pandas as pd

from scripts.optimize_zhu_walkline_early_start_parameters import (
    EarlyStartParameters,
    apply_same_stock_cooldown,
    classification_metrics,
    generate_candidates,
    parameter_mask,
)


def test_cooldown_does_not_use_forward_return() -> None:
    rows = pd.DataFrame(
        {
            "asof_date": pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-09"]),
            "stock_id": ["2330", "2330", "2330"],
            "signal_trade_index": [10, 11, 15],
            "d5_adjusted_return_pct": [-20.0, 50.0, -10.0],
        }
    )
    baseline = apply_same_stock_cooldown(rows)["same_stock_cooldown"].tolist()
    rows["d5_adjusted_return_pct"] *= -1
    changed = apply_same_stock_cooldown(rows)["same_stock_cooldown"].tolist()

    assert baseline == [True, False, True]
    assert changed == baseline


def test_stage_mask_cannot_use_later_snapshot_columns() -> None:
    rows = _model_rows()
    parameters = EarlyStartParameters(
        stage="T3_EARLY_TURN",
        t5_volume_ratio_max=0.75,
        t3_daily_return_min_pct=0.0,
    )
    baseline = parameter_mask(rows, parameters)
    rows.loc[:, ["t1_daily_return_pct", "t1_day_volume_ratio_20"]] = -999.0

    changed = parameter_mask(rows, parameters)

    pd.testing.assert_series_equal(baseline, changed)


def test_search_space_is_bounded_by_stage() -> None:
    grid = {
        "t5_volume_ratio_max": [0.55, 0.75],
        "t5_require_positive_ma20_slope": [False, True],
        "t3_daily_return_min_pct": [0.0, 1.0],
        "t3_k_change_min": [None, 0.0],
        "t1_daily_return_min_pct": [0.0, 1.0],
        "t1_volume_ratio_min": [0.7, 1.0],
        "t1_require_above_ma20": [False, True],
    }

    assert len(list(generate_candidates("T5_SETUP", grid))) == 4
    assert len(list(generate_candidates("T3_EARLY_TURN", grid))) == 16
    assert len(list(generate_candidates("T1_PRICE_VOLUME_CONFIRM", grid))) == 128


def test_metrics_include_precision_recall_and_balanced_accuracy() -> None:
    rows = _model_rows()
    selected = pd.Series([True, False, True, False])

    metrics = classification_metrics(rows, selected, split="HOLDOUT")

    assert metrics["precision_gain_ge10"] == 0.5
    assert metrics["recall_gain_ge10"] == 0.5
    assert metrics["balanced_accuracy_gain_ge10"] == 0.5
    assert metrics["selected_rows"] == 2


def _model_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asof_date": pd.to_datetime(
                ["2026-05-01", "2026-05-04", "2026-06-01", "2026-06-02"]
            ),
            "stock_id": ["1101", "1102", "1103", "1104"],
            "split": ["HOLDOUT"] * 4,
            "target_gain_ge10": [True, True, False, False],
            "target_gain_ge20": [True, False, False, False],
            "target_loss": [False, False, True, True],
            "d5_adjusted_return_pct": [25.0, 12.0, -3.0, -8.0],
            "t5_day_volume_ratio_20": [0.5, 0.8, 0.5, 0.8],
            "t5_sma20_slope_5d_pct": [1.0, 1.0, -1.0, -1.0],
            "t3_daily_return_pct": [1.0, 1.0, 1.0, -1.0],
            "t3_kd_k_change_1d": [2.0, 2.0, -1.0, -1.0],
            "t1_daily_return_pct": [1.0, 1.0, 1.0, -1.0],
            "t1_day_volume_ratio_20": [0.8, 0.8, 0.8, 0.8],
            "t1_close_to_sma20_pct": [1.0, 1.0, -1.0, -1.0],
        }
    )
