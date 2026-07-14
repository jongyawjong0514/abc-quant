from __future__ import annotations

import pandas as pd

from scripts.backtest_zhu_walkline_driver_screen import (
    build_same_count_driver_controls,
    build_same_count_baselines,
    compute_rolling_window_metrics,
    run_driver_screen_backtest,
    score_driver_screen,
)


def test_driver_score_uses_asof_features_not_forward_return() -> None:
    candidates = pd.DataFrame([_candidate("2330", forward_return_pct=5.0)])
    daily = pd.DataFrame([_daily("2330")])

    base = score_driver_screen(candidates, daily_features=daily)
    mutated = candidates.copy()
    mutated["forward_return_pct"] = 200.0
    rescored = score_driver_screen(mutated, daily_features=daily)

    assert base.iloc[0]["driver_score"] == rescored.iloc[0]["driver_score"]
    assert "sector_electronic_components" in base.iloc[0]["driver_reasons"]
    assert base.iloc[0]["driver_score"] >= 11


def test_same_count_baselines_match_driver_screen_daily_counts() -> None:
    universe = pd.DataFrame(
        [
            _candidate("2330", asof_date="2026-05-22", rise_score=80),
            _candidate("2317", asof_date="2026-05-22", rise_score=90),
            _candidate("2454", asof_date="2026-05-23", rise_score=70),
            _candidate("2408", asof_date="2026-05-23", rise_score=95),
        ]
    )
    selected = universe.iloc[[0, 2]].copy()

    baselines = build_same_count_baselines(selected, universe)

    for baseline in baselines.values():
        assert baseline.groupby("asof_date").size().to_dict() == {
            "2026-05-22": 1,
            "2026-05-23": 1,
        }
    assert baselines["same_count_top_rise"]["stock_id"].tolist() == ["2317", "2408"]


def test_same_count_driver_controls_draw_only_from_driver_universe() -> None:
    universe = pd.DataFrame(
        [
            {**_candidate("2330", asof_date="2026-05-22", rise_score=80), "driver_score": 12},
            {**_candidate("2317", asof_date="2026-05-22", rise_score=90), "driver_score": 11},
            {**_candidate("2454", asof_date="2026-05-23", rise_score=70), "driver_score": 12},
            {**_candidate("2408", asof_date="2026-05-23", rise_score=95), "driver_score": 11},
        ]
    )
    selected = universe.iloc[[0, 2]].copy()

    controls = build_same_count_driver_controls(selected, universe)

    for control in controls.values():
        assert control.groupby("asof_date").size().to_dict() == {
            "2026-05-22": 1,
            "2026-05-23": 1,
        }
        assert set(control["stock_id"]).issubset(set(universe["stock_id"]))
    assert controls["same_count_driver_score"]["stock_id"].tolist() == ["2330", "2454"]


def test_run_driver_screen_backtest_outputs_shadow_summary() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("2330", forward_return_pct=25.0, sector="電子零組件"),
            _candidate("2317", forward_return_pct=5.0, sector="半導體"),
        ]
    )
    daily = pd.DataFrame([_daily("2330"), _daily("2317")])
    price_rows = pd.DataFrame(
        [
            {"date": "2026-05-22", "stock_id": "2330", "close": 100.0},
            {"date": "2026-05-23", "stock_id": "2330", "close": 125.0},
            {"date": "2026-05-22", "stock_id": "2317", "close": 100.0},
            {"date": "2026-05-23", "stock_id": "2317", "close": 105.0},
        ]
    )

    result = run_driver_screen_backtest(
        candidates,
        daily_features=daily,
        price_rows=price_rows,
        min_driver_score=11,
        horizon_trading_days=1,
        rolling_window_days=1,
    )

    assert result["summary"]["mode"] == "shadow_observation_only"
    assert result["summary"]["formal_trade_effect"] is False
    assert result["screened_rows"]["stock_id"].tolist() == ["2330"]
    cohort_summary = pd.DataFrame(result["summary"]["cohort_summary"])
    selected = cohort_summary[cohort_summary["cohort"].eq("driver_screen")].iloc[0]
    assert selected["hit_rate_20pct"] == 1.0


def test_rolling_metrics_empty_output_keeps_report_schema() -> None:
    frame = pd.DataFrame([_candidate("2330")])

    rolling = compute_rolling_window_metrics(
        {"driver_screen": frame},
        rolling_window_days=20,
    )

    assert rolling.empty
    assert "window_end_date" in rolling.columns
    assert "avg_forward_return_pct" in rolling.columns


def test_required_hierarchy_gate_filters_after_market_sector_and_concept() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("2330", sector="電子零組件"),
            _candidate("2317", sector="電子零組件"),
        ]
    )
    daily = pd.DataFrame([_daily("2330"), _daily("2317")])
    price_rows = pd.DataFrame(
        [
            {"date": "2026-05-22", "stock_id": "2330", "close": 100.0},
            {"date": "2026-05-23", "stock_id": "2330", "close": 125.0},
            {"date": "2026-05-22", "stock_id": "2317", "close": 100.0},
            {"date": "2026-05-23", "stock_id": "2317", "close": 105.0},
        ]
    )
    membership = pd.DataFrame(
        [
            {"snapshot_id": "fixture", "concept_name": "AI", "stock_id": "2330"},
            {"snapshot_id": "fixture", "concept_name": "WEAK", "stock_id": "2317"},
        ]
    )
    rotation = pd.DataFrame(
        [
            _concept_rotation("AI", "CONCEPT_LEADING", 85.0),
            _concept_rotation("WEAK", "CONCEPT_WEAK", 30.0),
        ]
    )

    result = run_driver_screen_backtest(
        candidates,
        daily_features=daily,
        price_rows=price_rows,
        min_driver_score=11,
        horizon_trading_days=1,
        rolling_window_days=1,
        concept_membership=membership,
        concept_rotation=rotation,
        concept_snapshot_date="2026-07-09",
        concept_snapshot_manifest={"snapshot_id": "fixture", "snapshot_date": "2026-07-09"},
        hierarchy_gate="required",
    )

    assert set(result["driver_score_only_rows"]["stock_id"]) == {"2330", "2317"}
    assert result["screened_rows"]["stock_id"].tolist() == ["2330"]
    weak = result["scored_rows"].loc[result["scored_rows"]["stock_id"].eq("2317")].iloc[0]
    assert weak["hierarchy_gate_stage"] == "CONCEPT_NOT_LEADING"
    assert result["summary"]["hierarchy_gate"] == "required"


def test_future_concept_rotation_cannot_satisfy_asof_hierarchy_gate() -> None:
    candidates = pd.DataFrame([_candidate("2330", sector="電子零組件")])
    future_rotation = pd.DataFrame(
        [_concept_rotation("AI", "CONCEPT_LEADING", 90.0, asof_date="2026-05-23")]
    )

    result = run_driver_screen_backtest(
        candidates,
        daily_features=pd.DataFrame([_daily("2330")]),
        price_rows=pd.DataFrame(
            [
                {"date": "2026-05-22", "stock_id": "2330", "close": 100.0},
                {"date": "2026-05-23", "stock_id": "2330", "close": 125.0},
            ]
        ),
        min_driver_score=11,
        horizon_trading_days=1,
        rolling_window_days=1,
        concept_membership=pd.DataFrame(
            [{"snapshot_id": "fixture", "concept_name": "AI", "stock_id": "2330"}]
        ),
        concept_rotation=future_rotation,
        concept_snapshot_date="2026-07-09",
        hierarchy_gate="required",
    )

    assert result["screened_rows"].empty
    assert result["scored_rows"].iloc[0]["concept_state"] == "CONCEPT_DATA_UNAVAILABLE"


def _candidate(
    stock_id: str,
    *,
    asof_date: str = "2026-05-22",
    forward_return_pct: float = 20.0,
    sector: str = "電子零組件",
    rise_score: float = 80.0,
) -> dict[str, object]:
    return {
        "asof_date": asof_date,
        "stock_id": stock_id,
        "stock_name": "fixture",
        "close": 100.0,
        "forward_return_pct": forward_return_pct,
        "early_observation_rule": "STRICT_BREAKOUT",
        "review_bucket": "CLEAN_REVIEW",
        "rise_score": rise_score,
        "fall_risk_score": 0.0,
        "signal_stage": "CONFIRMED",
        "sector": sector,
        "sector_state": "SECTOR_LEADING",
        "market_state": "MARKET_RANGE_BOUND",
        "volume_state": "ATTACK_VOLUME",
        "kline_state": "ATTACK_RED_K",
        "sell_warning_type": "",
        "failure_type": "",
        "vol_ratio_20": 2.0,
        "stop_reference": "fixture",
    }


def _daily(stock_id: str) -> dict[str, object]:
    return {
        "date": pd.Timestamp("2026-05-22"),
        "stock_id": stock_id,
        "open_to_close_pct": 0.05,
        "gap_up_pct": 0.01,
        "close_location_in_bar": 0.9,
        "sma5": 92.0,
        "sma10": 90.0,
        "sma20": 85.0,
        "sma60": 75.0,
        "day_volume_ratio_20": 2.0,
        "intraday_return_rankpct": 0.9,
        "range_pos_20_rankpct": 0.9,
        "close_from_high_rankpct": 0.8,
    }


def _concept_rotation(
    concept_name: str,
    concept_state: str,
    score: float,
    *,
    asof_date: str = "2026-05-22",
) -> dict[str, object]:
    return {
        "snapshot_id": "fixture",
        "snapshot_date": "2026-07-09",
        "asof_date": asof_date,
        "concept_name": concept_name,
        "member_count": 10,
        "price_available_count": 10,
        "coverage_ratio": 1.0,
        "above_sma20_ratio": 0.8,
        "sma20_slope_positive_ratio": 0.8,
        "positive_return_5d_ratio": 0.8,
        "median_return_5d_pct": 5.0,
        "concept_strength_score": score,
        "concept_state": concept_state,
        "membership_mode": "static_current_backfill_user_authorized",
    }
