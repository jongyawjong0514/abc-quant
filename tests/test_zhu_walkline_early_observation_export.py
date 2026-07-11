from __future__ import annotations

from scripts.export_zhu_walkline_early_observation_candidates import (
    LABEL_TODO_COLUMNS,
    build_fast_precomputed_feature_matrix,
    select_early_observation_candidates,
)

import pandas as pd


def test_select_early_observation_candidates_keeps_strict_and_review_rows() -> None:
    frame = pd.DataFrame(
        [
            _row(
                "2330",
                rise_score=80,
                fall_risk_score=20,
                buy_type="RESISTANCE_BREAKOUT",
                buy_detail="RESISTANCE_BREAKOUT|SUPPORT_REBOUND",
                resistance_breakout=True,
            ),
            _row(
                "2357",
                rise_score=50,
                fall_risk_score=40,
                trigger_type="MA_RECLAIM",
                ma_state="MA_RECLAIM",
                signal_stage="FAILED",
                sell_warning_type="SUPPORT_BREAKDOWN",
                failure_type="NO_VOLUME_FOLLOW|SUPPORT_BREAK",
            ),
            _row("2408", market_state="MARKET_DOWNTREND", rise_score=90),
            _row("2412", sector_rotation_rank=20, rise_score=90),
            _row("2454", close_above_ma20=False, rise_score=95),
        ]
    )

    selected = select_early_observation_candidates(frame, max_per_day=None)

    assert selected["stock_id"].tolist() == ["2330", "2357"]
    strict = selected[selected["stock_id"] == "2330"].iloc[0]
    review = selected[selected["stock_id"] == "2357"].iloc[0]
    assert strict["early_observation_rule"] == "STRICT_BREAKOUT"
    assert strict["review_bucket"] == "CLEAN_REVIEW"
    assert review["early_observation_rule"] == "AGGRESSIVE_MA_RECLAIM_REVIEW"
    assert "REVIEW_WITH_WARNING" in review["review_bucket"]
    assert "NO_VOLUME_FOLLOW" in review["review_bucket"]
    assert review["label_user"] == ""
    for column in LABEL_TODO_COLUMNS:
        assert column in selected.columns


def test_select_early_observation_candidates_respects_max_per_day() -> None:
    frame = pd.DataFrame(
        [
            _row("2330", rise_score=80, fall_risk_score=20),
            _row("2317", rise_score=75, fall_risk_score=25),
        ]
    )

    selected = select_early_observation_candidates(frame, max_per_day=1)

    assert len(selected) == 1
    assert selected.iloc[0]["stock_id"] == "2330"


def test_select_early_observation_candidates_requires_positive_ma20_slope() -> None:
    frame = pd.DataFrame(
        [
            _row("2330", rise_score=80, ma20_slope=0.4),
            _row("2317", rise_score=90, ma20_slope=0.0),
            _row("2454", rise_score=95, ma20_slope=-0.1),
        ]
    )

    selected = select_early_observation_candidates(frame, max_per_day=None)

    assert selected["stock_id"].tolist() == ["2330"]
    assert selected.iloc[0]["ma20_slope"] == 0.4


def test_fast_precomputed_engine_ignores_future_rows_after_end_date() -> None:
    stock_info = pd.DataFrame(
        [{"stock_id": "2330", "stock_name": "台積電", "sector": "半導體", "market": "TWSE"}]
    )
    base = _fast_rows(future_high=120.0, future_volume=1_200_000.0)
    mutated = _fast_rows(future_high=999.0, future_volume=99_000_000.0)

    base_features = build_fast_precomputed_feature_matrix(
        base,
        stock_info=stock_info,
        start_date="2026-05-22",
        end_date="2026-05-22",
    )
    mutated_features = build_fast_precomputed_feature_matrix(
        mutated,
        stock_info=stock_info,
        start_date="2026-05-22",
        end_date="2026-05-22",
    )

    base_selected = select_early_observation_candidates(base_features, max_per_day=None)
    mutated_selected = select_early_observation_candidates(mutated_features, max_per_day=None)

    compare_columns = [
        "asof_date",
        "stock_id",
        "early_observation_rule",
        "buy_observation_type",
        "rise_score",
        "support_zone_1_label",
        "resistance_zone_1_label",
    ]
    assert not base_selected.empty
    assert base_selected[compare_columns].to_dict("records") == mutated_selected[
        compare_columns
    ].to_dict("records")


def _row(
    stock_id: str,
    *,
    rise_score: float = 70,
    fall_risk_score: float = 20,
    market_state: str = "MARKET_PULLBACK_IN_UPTREND",
    sector_rotation_rank: int = 3,
    sector_state: str = "SECTOR_LEADING",
    buy_type: str = "RESISTANCE_BREAKOUT",
    buy_detail: str = "RESISTANCE_BREAKOUT",
    trigger_type: str = "RANGE_BREAKOUT",
    ma_state: str = "BULL_ALIGNMENT",
    ma20_slope: float = 0.25,
    close_above_ma20: bool = True,
    resistance_breakout: bool = True,
    signal_stage: str = "CONFIRMED",
    sell_warning_type: str = "",
    failure_type: str = "",
) -> dict[str, object]:
    return {
        "asof_date": "2026-05-22",
        "stock_id": stock_id,
        "stock_name": "fixture",
        "close": 100.0,
        "rise_score": rise_score,
        "grade": "B",
        "fall_risk_score": fall_risk_score,
        "signal_stage": signal_stage,
        "trigger_type": trigger_type,
        "buy_observation_type": buy_type,
        "buy_observation_detail_types": buy_detail,
        "buy_trigger_price": 99.0,
        "buy_trigger_price_role": "TRIGGERED_PRICE",
        "confirm_price": 101.0,
        "invalidation_price": 95.0,
        "support_zone_1_low": 95.0,
        "support_zone_1_label": "95.00",
        "resistance_zone_1_label": "101.00",
        "ma_state": ma_state,
        "ma20_slope": ma20_slope,
        "trend_state": "UPTREND",
        "kline_state": "ATTACK_RED_K",
        "volume_state": "ATTACK_VOLUME",
        "vol_ratio_20": 1.6,
        "close_above_ma5": True,
        "close_above_ma20": close_above_ma20,
        "support_zone_holding_today": False,
        "resistance_zone_breakout_today": resistance_breakout,
        "sector": "fixture-sector",
        "sector_rotation_rank": sector_rotation_rank,
        "sector_state": sector_state,
        "market_state": market_state,
        "failure_type": failure_type,
        "sell_warning_type": sell_warning_type,
        "stop_reference": "跌破支撐區 95.00 重新評估",
    }


def _fast_rows(*, future_high: float, future_volume: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    closes = [99.0, 100.0, 101.0, 100.5, 102.0, 103.0, 106.0, 108.0, 109.0]
    dates = pd.date_range("2026-05-15", periods=len(closes), freq="D")
    for index, (date, close) in enumerate(zip(dates, closes, strict=True)):
        high = max(close + 1.0, future_high) if date.strftime("%Y-%m-%d") == "2026-05-23" else close + 1.0
        volume = future_volume if date.strftime("%Y-%m-%d") == "2026-05-23" else 1_000_000.0
        if date.strftime("%Y-%m-%d") == "2026-05-22":
            high = 107.0
            volume = 1_500_000.0
        rows.append(
            {
                "date": date,
                "stock_id": "2330",
                "open": close - 1.0,
                "high": high,
                "low": close - 2.0,
                "close": close,
                "volume": volume,
                "previous_close": closes[index - 1] if index else close - 1.0,
                "open_to_close_pct": 0.03,
                "close_location_in_bar": 0.85,
                "range_pos_20": 0.8,
                "sma5": close - 2.0,
                "sma10": close - 3.0,
                "sma20": close - 4.0,
                "sma60": close - 10.0,
                "sma5_gap": 0.02,
                "sma10_gap": 0.03,
                "sma20_gap": 0.04,
                "sma60_gap": 0.10,
                "volume_ma5": 1_000_000.0,
                "volume_ma20": 1_000_000.0,
                "day_volume_ratio_20": 1.5,
                "intraday_return_rankpct": 0.9,
                "sma20_gap_rankpct": 0.9,
                "range_pos_20_rankpct": 0.9,
                "day_volume_ratio_20_rankpct": 0.8,
                "upper_tail_flag": 0,
                "volume_exhaustion_flag": 0,
                "late_chase_risk_flag": 0,
            }
        )
    return pd.DataFrame(rows)
