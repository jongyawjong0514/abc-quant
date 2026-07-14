from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.replay_zhu_walkline_full_market_early_start import (
    FixedFullMarketRule,
    build_four_component_bucket_metrics,
    build_full_market_feature_rows,
    evaluate_full_market_screen,
    fixed_early_start_mask,
    link_future_kd_confirmations,
    merge_pit_universe,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_fixed_rule_mask_is_invariant_to_forward_evaluator_mutation() -> None:
    rows = pd.DataFrame(
        {
            "kd_k9": [19.0, 30.0],
            "kd_k_change_1d": [3.0, 3.0],
            "daily_return_pct": [1.5, 1.5],
            "day_volume_ratio_20": [0.7, 0.7],
            "close_to_sma20_pct": [-1.0, -1.0],
            "distance_from_trailing_5d_low_pct": [4.0, 4.0],
            "d5_adjusted_return_pct": [20.0, -20.0],
            "future_kd_signal_date": ["2026-06-10", ""],
        }
    )
    rule = FixedFullMarketRule(20, 2, 1, 0.8, 0, 8)
    baseline = fixed_early_start_mask(rows, rule)
    rows["d5_adjusted_return_pct"] *= -100
    rows["future_kd_signal_date"] = "2099-01-01"

    changed = fixed_early_start_mask(rows, rule)

    pd.testing.assert_series_equal(baseline, changed)
    assert baseline.tolist() == [True, False]


def test_feature_history_is_causal_when_post_cutoff_prices_are_appended() -> None:
    dates = pd.bdate_range("2025-01-02", periods=90)
    cutoff = dates[-6]
    baseline = build_full_market_feature_rows(
        _prices(dates[:-5]),
        signal_start=cutoff.strftime("%Y-%m-%d"),
        signal_end=cutoff.strftime("%Y-%m-%d"),
    )
    mutated = _prices(dates)
    mutated.loc[mutated["date"].gt(cutoff), "close"] = 9999.0
    replay = build_full_market_feature_rows(
        mutated,
        signal_start=cutoff.strftime("%Y-%m-%d"),
        signal_end=cutoff.strftime("%Y-%m-%d"),
    )

    pd.testing.assert_frame_equal(baseline, replay, check_dtype=False)


def test_pit_merge_rejects_future_effective_source_date() -> None:
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01"]),
            "stock_id": ["2330"],
            "close": [100.0],
        }
    )
    pit = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01"]),
            "stock_id": ["2330"],
            "stock_name": ["台積電"],
            "market": ["TWSE"],
            "effective_source_date": pd.to_datetime(["2026-06-02"]),
            "listing_date": pd.to_datetime(["1994-09-05"]),
            "pit_quality_rank": [1],
        }
    )

    with pytest.raises(ValueError, match="PIT universe date violation"):
        merge_pit_universe(daily, pit)


def test_future_kd_linkage_uses_trade_day_distance_and_marks_censoring() -> None:
    dates = pd.bdate_range("2026-06-01", periods=15)
    daily = pd.DataFrame(
        {
            "date": dates,
            "stock_id": "2330",
            "signal_trade_index": range(15),
            "close": [100.0 + value for value in range(15)],
        }
    )
    candidates = pd.DataFrame(
        {
            "asof_date": [dates[2].strftime("%Y-%m-%d"), dates[10].strftime("%Y-%m-%d")],
            "stock_id": ["2330", "2330"],
            "signal_trade_index": [2, 10],
            "close": [102.0, 110.0],
        }
    )
    confirmed = pd.DataFrame(
        {
            "asof_date": [dates[6].strftime("%Y-%m-%d")],
            "stock_id": ["2330"],
            "close": [106.0],
        }
    )

    linked = link_future_kd_confirmations(
        candidates,
        confirmed_events=confirmed,
        daily_features=daily,
        minimum_lead_days=2,
        maximum_lead_days=10,
    )

    assert bool(linked.iloc[0]["future_kd_confirmation_within_window"])
    assert linked.iloc[0]["future_kd_lead_trade_days"] == 4
    assert bool(linked.iloc[0]["future_kd_linkage_mature"])
    assert not bool(linked.iloc[1]["future_kd_linkage_mature"])


def test_full_market_metric_uses_all_eligible_rows_for_recall() -> None:
    rows = pd.DataFrame(
        {
            "asof_date": ["2026-06-01"] * 4,
            "stock_id": ["1001", "1002", "1003", "1004"],
            "early_start_candidate": [True, True, False, False],
            "d5_adjusted_return_pct": [12.0, -2.0, 15.0, -1.0],
        }
    )

    metric = evaluate_full_market_screen(
        rows,
        scope="test",
        target_return_pct=10.0,
        large_gain_return_pct=20.0,
    )

    assert metric["precision_gain_ge10"] == 0.5
    assert metric["recall_gain_ge10"] == 0.5
    assert metric["balanced_accuracy_gain_ge10"] == 0.5
    assert metric["tp"] == metric["fp"] == metric["fn"] == metric["tn"] == 1


def test_replay_config_contains_one_scalar_rule_not_a_search_grid() -> None:
    config = yaml.safe_load(
        (
            REPO_ROOT / "config" / "zhu_walkline_full_market_early_start_replay.yaml"
        ).read_text(encoding="utf-8")
    )

    assert "search_grid" not in config
    assert all(not isinstance(value, list) for value in config["fixed_rule"].values())
    assert set(config["universe_guards"]["markets"]) == {"TWSE", "TPEX"}


def test_four_component_buckets_are_descriptive_after_selection() -> None:
    rows = pd.DataFrame(
        {
            "primary_evaluation_eligible": [True, True, True],
            "shadow_strength_complete": [True, True, False],
            "shadow_strength_score": [25.0, 75.0, 100.0],
            "d5_adjusted_return_pct": [-1.0, 12.0, 30.0],
            "future_kd_linkage_mature": [True, True, True],
            "future_kd_confirmation_within_window": [False, True, True],
        }
    )

    buckets = build_four_component_bucket_metrics(rows)

    assert buckets["shadow_strength_score"].tolist() == [25.0, 75.0]
    assert buckets["d5_gain_ge10_rate"].tolist() == [0.0, 1.0]
    assert buckets["future_kd_linked_rate"].tolist() == [0.0, 1.0]


def _prices(dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series(range(100, 100 + len(dates)), dtype=float)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": "2330",
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000_000.0,
        }
    )
