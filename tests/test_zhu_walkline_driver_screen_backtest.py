from __future__ import annotations

import pandas as pd

from scripts.backtest_zhu_walkline_driver_screen import (
    build_same_count_baselines,
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
