import pandas as pd
import pytest

from abc_quant.features.early_start_trajectory import (
    EarlyTrajectoryRule,
    build_event_trajectory,
    build_t1_baseline_alerts,
    earliest_alert_rows,
    evaluate_event_alerts,
    generate_trajectory_rules,
    trajectory_rule_mask,
)
from scripts.analyze_zhu_walkline_kd_d5_lead_snapshots import prepare_adjusted_history
from scripts.optimize_zhu_walkline_d10_trajectory import build_purged_temporal_stress


def test_trajectory_contains_every_exact_d10_through_d_row() -> None:
    dates = pd.bdate_range("2025-09-01", periods=100)
    history = prepare_adjusted_history(_history(dates))
    signal_date = dates[-1]

    rows = build_event_trajectory(_events(signal_date), history)

    assert rows["relative_day"].tolist() == [
        "D-10",
        "D-9",
        "D-8",
        "D-7",
        "D-6",
        "D-5",
        "D-4",
        "D-3",
        "D-2",
        "D-1",
        "D",
    ]
    assert rows.iloc[0]["observation_date"] == dates[-11].strftime("%Y-%m-%d")
    assert rows.iloc[-1]["observation_date"] == signal_date.strftime("%Y-%m-%d")


def test_rule_mask_ignores_forward_outcome_mutation() -> None:
    rows = _rule_rows()
    rule = EarlyTrajectoryRule(30, 0, 0, 0.8, 0, 4)
    baseline = trajectory_rule_mask(rows, rule)
    rows["d5_adjusted_return_pct"] *= -100
    rows["evaluator_return_observation_to_signal_pct"] = 999.0

    changed = trajectory_rule_mask(rows, rule)

    pd.testing.assert_series_equal(baseline, changed)


def test_earliest_alert_keeps_largest_lead_day() -> None:
    rows = _rule_rows()
    mask = pd.Series([True, True, False])

    selected = earliest_alert_rows(rows, mask)

    assert len(selected) == 1
    assert selected.iloc[0]["lead_days"] == 5


def test_t1_baseline_reproduces_prespecified_chain() -> None:
    rows = pd.DataFrame(
        [
            _baseline_row(5, volume=0.7, daily=-1.0),
            _baseline_row(3, volume=0.6, daily=0.5),
            _baseline_row(1, volume=0.8, daily=1.0),
        ]
    )

    alerts = build_t1_baseline_alerts(rows)

    assert len(alerts) == 1
    assert alerts.iloc[0]["lead_days"] == 1


def test_search_grid_is_bounded() -> None:
    grid = {
        "max_k": [20, 30],
        "min_k_change_1d": [0, 1],
        "min_daily_return_pct": [0, 1],
        "max_volume_ratio_20": [0.8],
        "max_close_to_sma20_pct": [0],
        "max_distance_from_trailing_5d_low_pct": [4],
    }

    assert len(list(generate_trajectory_rules(grid))) == 8


def test_alert_to_d5_metric_uses_same_endpoint_from_earlier_alert() -> None:
    events = pd.DataFrame(
        [
            {
                "signal_date": "2026-06-05",
                "stock_id": "2330",
                "stock_name": "台積電",
                "split": "HOLDOUT",
                "target_gain_ge10": True,
                "d5_adjusted_return_pct": 10.0,
            }
        ]
    )
    alerts = pd.DataFrame(
        [
            {
                "signal_date": "2026-06-05",
                "stock_id": "2330",
                "lead_days": 4,
                "evaluator_return_observation_to_signal_pct": 10.0,
                "distance_from_trailing_5d_low_pct": 2.0,
            }
        ]
    )

    metric = evaluate_event_alerts(events, alerts, split="HOLDOUT")

    assert metric["median_alert_to_d5_adjusted_return_pct"] == pytest.approx(21.0)
    assert metric["gain_ge20_from_alert_to_d5_rate"] == 1.0
    assert metric["loss_from_alert_to_d5_rate"] == 0.0


def test_purged_stress_waits_for_prior_split_labels_and_full_d10_window() -> None:
    events = pd.DataFrame(
        [
            _purge_event("2026-01-08", "1001", "DISCOVERY", "2026-01-15"),
            _purge_event("2026-01-24", "1002", "VALIDATION", "2026-02-15"),
            _purge_event("2026-01-26", "1003", "VALIDATION", "2026-02-15"),
            _purge_event("2026-02-24", "1004", "HOLDOUT", "2026-03-15"),
            _purge_event("2026-02-26", "1005", "HOLDOUT", "2026-03-15"),
        ]
    )
    trajectory = pd.DataFrame(
        [
            _purge_trajectory("2026-01-08", "1001", "2025-12-22"),
            _purge_trajectory("2026-01-24", "1002", "2026-01-14"),
            _purge_trajectory("2026-01-26", "1003", "2026-01-16"),
            _purge_trajectory("2026-02-24", "1004", "2026-02-14"),
            _purge_trajectory("2026-02-26", "1005", "2026-02-16"),
        ]
    )
    alerts = pd.DataFrame(
        [
            {
                "signal_date": row.signal_date,
                "stock_id": row.stock_id,
                "lead_days": 4,
                "evaluator_return_observation_to_signal_pct": 5.0,
                "distance_from_trailing_5d_low_pct": 2.0,
            }
            for row in events.itertuples(index=False)
        ]
    )

    stress = build_purged_temporal_stress(
        trajectory,
        event_rows=events,
        baseline_alerts=alerts,
        selected_alerts=alerts,
    )

    validation = stress[stress["split"].eq("VALIDATION")]
    holdout = stress[stress["split"].eq("HOLDOUT")]
    assert validation["prior_label_freeze_date"].eq("2026-01-15").all()
    assert validation["purged_split_rows"].eq(1).all()
    assert holdout["prior_label_freeze_date"].eq("2026-02-15").all()
    assert holdout["purged_split_rows"].eq(1).all()


def _events(signal_date: pd.Timestamp) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asof_date": signal_date,
                "stock_id": "2330",
                "stock_name": "台積電",
                "d5_adjusted_return_pct": 12.0,
            }
        ]
    )


def _history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    close = pd.Series(range(100, 100 + size), dtype=float)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "adj_open": close - 0.5,
            "adj_high": close + 1.0,
            "adj_low": close - 1.0,
            "adj_close": close,
            "volume": pd.Series(range(1000, 1000 + size), dtype=float),
        }
    )


def _rule_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "signal_date": ["2026-06-05"] * 3,
            "stock_id": ["2330"] * 3,
            "lead_days": [5, 3, 1],
            "kd_k9": [20.0, 25.0, 40.0],
            "kd_k_change_1d": [1.0, 2.0, 3.0],
            "daily_return_pct": [0.5, 1.0, 2.0],
            "day_volume_ratio_20": [0.5, 0.7, 1.5],
            "close_to_sma20_pct": [-2.0, -1.0, 3.0],
            "distance_from_trailing_5d_low_pct": [1.0, 2.0, 5.0],
            "d5_adjusted_return_pct": [12.0] * 3,
            "evaluator_return_observation_to_signal_pct": [8.0, 5.0, 1.0],
        }
    )


def _baseline_row(lead: int, *, volume: float, daily: float) -> dict:
    return {
        "signal_date": "2026-06-05",
        "stock_id": "2330",
        "lead_days": lead,
        "day_volume_ratio_20": volume,
        "daily_return_pct": daily,
    }


def _purge_event(
    signal_date: str,
    stock_id: str,
    split: str,
    d5_close_date: str,
) -> dict[str, object]:
    return {
        "signal_date": signal_date,
        "stock_id": stock_id,
        "stock_name": stock_id,
        "split": split,
        "d5_close_date": d5_close_date,
        "d5_adjusted_return_pct": 12.0,
        "target_gain_ge10": True,
    }


def _purge_trajectory(
    signal_date: str,
    stock_id: str,
    observation_date: str,
) -> dict[str, object]:
    return {
        "signal_date": signal_date,
        "stock_id": stock_id,
        "observation_date": observation_date,
        "lead_days": 10,
    }
