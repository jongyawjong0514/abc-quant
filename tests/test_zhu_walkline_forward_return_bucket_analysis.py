from __future__ import annotations

import pandas as pd

from scripts.analyze_zhu_walkline_forward_return_buckets import (
    assign_forward_return_bucket,
    build_forward_return_bucket_analysis,
)


def test_assign_forward_return_bucket_boundaries() -> None:
    assert assign_forward_return_bucket(19.99) == ("", "", 0)
    assert assign_forward_return_bucket(20.0) == ("GAIN_21_30", "21%-30%", 1)
    assert assign_forward_return_bucket(30.999) == ("GAIN_21_30", "21%-30%", 1)
    assert assign_forward_return_bucket(31.0) == ("GAIN_31_40", "31%-40%", 2)
    assert assign_forward_return_bucket(41.0) == ("GAIN_41_50", "41%-50%", 3)
    assert assign_forward_return_bucket(51.0) == ("GAIN_GT_50", ">50%", 4)


def test_build_forward_return_bucket_analysis_quantifies_category_and_numeric_drivers() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("2330", 25.0, sector="半導體", rise_score=80, ma20_slope=1.0),
            _candidate("2317", 35.0, sector="半導體", rise_score=82, ma20_slope=1.2),
            _candidate("2408", 45.0, sector="半導體", rise_score=84, ma20_slope=1.4),
            _candidate("2367", 65.0, sector="電子零組件", rise_score=96, ma20_slope=2.5),
        ]
    )
    daily_features = pd.DataFrame(
        [
            _daily("2330", open_to_close_pct=0.01),
            _daily("2317", open_to_close_pct=0.02),
            _daily("2408", open_to_close_pct=0.03),
            _daily("2367", open_to_close_pct=0.08),
        ]
    )

    analysis = build_forward_return_bucket_analysis(
        candidates,
        daily_features=daily_features,
        min_category_count=1,
    )

    summary = analysis["bucket_summary"]
    assert summary["return_bucket"].tolist() == [
        "GAIN_21_30",
        "GAIN_31_40",
        "GAIN_41_50",
        "GAIN_GT_50",
    ]
    assert summary["rows"].tolist() == [1, 1, 1, 1]
    drivers = analysis["reason_drivers"]
    gt50_drivers = drivers[drivers["return_bucket"].eq("GAIN_GT_50")]
    assert "sector=電子零組件" in gt50_drivers["driver"].tolist()
    assert any(driver.startswith("HIGH_") for driver in gt50_drivers["driver"].astype(str))
    assert analysis["summary"]["mode"] == "shadow_observation_only"
    assert analysis["summary"]["formal_trade_effect"] is False


def _candidate(
    stock_id: str,
    forward_return_pct: float,
    *,
    sector: str,
    rise_score: float,
    ma20_slope: float,
) -> dict[str, object]:
    return {
        "asof_date": "2026-05-22",
        "stock_id": stock_id,
        "stock_name": "fixture",
        "close": 100.0,
        "forward_close": 100.0 * (1 + forward_return_pct / 100.0),
        "forward_return_pct": forward_return_pct,
        "early_observation_rule": "STRICT_BREAKOUT",
        "review_bucket": "CLEAN_REVIEW",
        "rank_by_early_rule": 1,
        "rank_by_rise": 1,
        "rise_score": rise_score,
        "grade": "A",
        "fall_risk_score": 0.0,
        "signal_stage": "CONFIRMED",
        "trigger_type": "RANGE_BREAKOUT",
        "buy_observation_type": "RESISTANCE_BREAKOUT",
        "buy_trigger_price_role": "TRIGGERED_PRICE",
        "confirm_price": 105.0,
        "invalidation_price": 95.0,
        "support_zone_1_label": 95.0,
        "ma_state": "BULL_ALIGNMENT",
        "ma20": 90.0,
        "ma20_slope": ma20_slope,
        "ma120": 80.0,
        "trend_state": "UPTREND",
        "kline_state": "ATTACK_RED_K",
        "volume_state": "ATTACK_VOLUME",
        "vol_ratio_20": 1.5,
        "sector": sector,
        "sector_rotation_rank": 1,
        "sector_state": "SECTOR_LEADING",
        "market_state": "MARKET_RANGE_BOUND",
    }


def _daily(stock_id: str, *, open_to_close_pct: float) -> dict[str, object]:
    return {
        "date": pd.Timestamp("2026-05-22"),
        "stock_id": stock_id,
        "open": 98.0,
        "high": 102.0,
        "low": 97.0,
        "volume": 1_000_000,
        "previous_close": 97.0,
        "open_to_close_pct": open_to_close_pct,
        "gap_up_pct": 0.01,
        "close_from_high_pct": -0.01,
        "low_from_open_pct": -0.01,
        "close_location_in_bar": 0.8,
        "range_pos_20": 0.9,
        "sma5": 94.0,
        "sma10": 92.0,
        "sma60": 75.0,
        "sma5_gap": 0.06,
        "sma10_gap": 0.08,
        "sma20_gap": 0.11,
        "sma60_gap": 0.33,
        "volume_ratio_5_20": 1.2,
        "day_volume_ratio_20": 1.5,
        "intraday_return_rankpct": 0.9,
        "sma20_gap_rankpct": 0.9,
        "day_volume_ratio_20_rankpct": 0.8,
        "range_pos_20_rankpct": 0.9,
        "close_from_high_rankpct": 0.8,
    }
