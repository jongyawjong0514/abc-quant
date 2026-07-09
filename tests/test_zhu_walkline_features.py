import pandas as pd
import pytest

from abc_quant.data.local_tw_loader import DataQualityReport, LocalTwDataBundle
from abc_quant.features.walkline_features import compute_walkline_features, _cluster_price_zones
from abc_quant.signals.zhu_walkline_shadow import build_zhu_walkline_shadow_result, _score_features


def _mock_price_frame(stock_id: str = "2330", bearish: bool = False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2026-06-01", periods=30, freq="D")
    for index, dt in enumerate(dates):
        close = 50.0 + index if not bearish else 80.0 - index
        open_ = close - 1.0 if not bearish else close + 1.0
        if index == len(dates) - 1 and not bearish:
            open_ = close - 4.0
            close = close + 3.0
        if index == len(dates) - 1 and bearish:
            open_ = close + 4.0
            close = close - 3.0
        rows.append(
            {
                "date": dt,
                "stock_id": stock_id,
                "open": open_,
                "high": max(open_, close) + 1.0,
                "low": min(open_, close) - 1.0,
                "close": close,
                "volume": 1000.0 + index * 10,
            }
        )
    return pd.DataFrame(rows)


def test_walkline_features_compute_core_fields() -> None:
    features = compute_walkline_features(_mock_price_frame(), asof_date="2026-06-30")
    row = features.iloc[0]

    assert row["ma5"] == pytest.approx((75.0 + 76.0 + 77.0 + 78.0 + 82.0) / 5.0)
    assert row["ma10"] > row["ma20"]
    assert bool(row["ma_bull_alignment"])
    assert bool(row["close_above_prev_high"])
    assert bool(row["long_red_k"])
    assert row["upper_shadow_pct"] == pytest.approx(1.0 / 82.0)
    assert row["lower_shadow_pct"] == pytest.approx(1.0 / 82.0)
    assert row["vol_ratio_5"] > 0
    assert row["support_1"] <= row["close"]
    assert row["resistance_1"] >= row["close"]
    assert row["support_zone_1_low"] <= row["support_zone_1_high"] <= row["close"]
    assert row["resistance_zone_1_low"] <= row["resistance_zone_1_high"]
    assert isinstance(row["support_zone_1_label"], str)
    assert isinstance(row["resistance_zone_1_label"], str)
    assert "round_number" in row["support_zone_1_sources"]
    assert 0 <= row["risk_reward_proxy"] or pd.isna(row["risk_reward_proxy"])


def test_price_zone_clustering_merges_nearby_levels() -> None:
    zones = _cluster_price_zones(
        [
            (100.0, "prev_low"),
            (101.4, "ma5"),
            (106.0, "swing_low_20d"),
        ]
    )

    assert zones[0]["low"] == pytest.approx(100.0)
    assert zones[0]["high"] == pytest.approx(101.4)
    assert zones[0]["sources"] == "ma5|prev_low"
    assert zones[1]["low"] == pytest.approx(106.0)


def test_walkline_features_detect_bearish_alignment() -> None:
    features = compute_walkline_features(_mock_price_frame("2317", bearish=True), asof_date="2026-06-30")
    row = features.iloc[0]

    assert bool(row["ma_bear_alignment"])
    assert row["ma_state"] in {"BEAR_ALIGNMENT", "MA_BREAK"}
    assert row["kline_state"] in {"LONG_BLACK_K", "BREAKDOWN_K", "UPPER_SHADOW_SUPPLY"}


def test_zhu_walkline_scores_stay_bounded() -> None:
    price = pd.concat([_mock_price_frame("2330"), _mock_price_frame("2317", bearish=True)])
    quality = DataQualityReport(sqlite_path="mock.sqlite", sqlite_exists=True)
    bundle = LocalTwDataBundle(
        asof_date="2026-06-30",
        requested_asof="2026-06-30",
        price_history=price,
        stock_info=pd.DataFrame(
            {
                "stock_id": ["2330", "2317"],
                "stock_name": ["台積電", "鴻海"],
                "sector": ["半導體", "電子零組件"],
                "market": ["TWSE", "TWSE"],
            }
        ),
        chip_history=pd.DataFrame(),
        margin_history=pd.DataFrame(),
        holder_latest=pd.DataFrame(),
        market_history=pd.DataFrame(),
        sector_sentiment=pd.DataFrame(),
        stock_context=pd.DataFrame(),
        class_membership=pd.DataFrame(),
        data_quality=quality,
    )
    result = build_zhu_walkline_shadow_result(
        bundle,
        concept_map={"SEMICONDUCTOR": ["2330"]},
        web_records=[],
        top_n=10,
        web_research_used=False,
        config={"scoring": {"web_score_cap": 5}},
    )

    assert result.feature_matrix["rise_score"].between(0, 100).all()
    assert result.feature_matrix["fall_risk_score"].between(0, 100).all()
    assert result.mode == "shadow_observation_only"
    assert result.formal_champion_changed is False
    assert result.formal_trade_effect is False
    assert {"signal_stage", "trigger_type", "invalid_price", "confirm_price", "failure_type"}.issubset(
        result.feature_matrix.columns
    )


def test_market_state_caps_bullish_grades() -> None:
    weak = _score_one_market_state("MARKET_WEAK_REBOUND")
    down = _score_one_market_state("MARKET_DOWNTREND")
    high_risk = _score_one_market_state("MARKET_HIGH_RISK_BREAKDOWN")

    assert weak.loc[0, "grade"] == "B"
    assert down.loc[0, "grade"] == "C"
    assert high_risk.loc[0, "grade"] == ""


def test_failure_type_flags_supply_institutional_and_margin_risks() -> None:
    frame = _scoring_frame()
    frame.loc[0, "distance_to_60d_high"] = 0.02
    frame.loc[0, "vol_ratio_20"] = 1.8
    frame.loc[0, "upper_shadow_pct"] = 0.04
    frame.loc[0, "close_position_in_range"] = 0.4
    frame.loc[0, "institutional_total_buy_sell"] = 1000.0
    frame.loc[0, "black_k"] = True
    frame.loc[0, "close"] = 95.0
    frame.loc[0, "ma20"] = 100.0
    frame.loc[0, "margin_change_1d"] = 500.0

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    failure_type = frame.loc[0, "failure_type"]
    assert "SUPPLY_PRESSURE" in failure_type
    assert "INSTITUTIONAL_DIVERGENCE" in failure_type
    assert "MARGIN_CROWDING" in failure_type
    assert frame.loc[0, "signal_stage"] == "FAILED"
    assert frame.loc[0, "grade"] == ""


def _score_one_market_state(market_state: str) -> pd.DataFrame:
    frame = _scoring_frame()
    _score_features(
        frame,
        market={"market_state": market_state, "market_score": 10, "market_risk_score": 0},
        config={"scoring": {"rise_min_a": 80, "rise_min_b": 70, "rise_min_c": 60, "web_score_cap": 5}},
    )
    return frame


def _scoring_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stock_id": ["2330"],
            "close": [100.0],
            "ma5": [98.0],
            "ma20": [95.0],
            "prev_high": [99.0],
            "prev_low": [94.0],
            "support_1": [95.0],
            "support_2": [90.0],
            "resistance_1": [102.0],
            "distance_to_60d_high": [0.1],
            "vol_ratio_20": [1.6],
            "upper_shadow_pct": [0.01],
            "close_position_in_range": [0.9],
            "institutional_total_buy_sell": [0.0],
            "black_k": [False],
            "return_1d": [0.03],
            "support_broken_today": [False],
            "margin_change_1d": [0.0],
            "margin_consecutive_increase_days": [0.0],
            "close_above_prev_high": [True],
            "close_above_ma5": [True],
            "volume_expansion": [True],
            "ma_reclaim_20": [False],
            "ma_reclaim_10": [False],
            "ma_reclaim_5": [False],
            "hammer_like": [False],
            "red_k": [True],
            "failed_breakdown": [False],
            "trend_state": ["UPTREND"],
            "low_volume_pullback": [False],
            "failed_breakout": [False],
            "sector_state": ["SECTOR_LEADING"],
            "sector_risk_score": [10.0],
            "high_volume_upper_shadow": [False],
            "margin_risk_score": [0.0],
            "sector_strength_score": [100.0],
            "concept_strength_score": [100.0],
            "concept_risk_score": [0.0],
            "institutional_score": [10.0],
            "institutional_selling_score": [0.0],
            "big_holder_score": [5.0],
            "margin_score": [5.0],
            "event_score_for_rise": [5.0],
            "event_score_for_fall": [0.0],
            "supply_pressure_score": [0.0],
            "kline_state": ["ATTACK_RED_K"],
            "ma_state": ["BULL_ALIGNMENT"],
            "volume_state": ["ATTACK_VOLUME"],
            "market_state": ["MARKET_RANGE_BOUND"],
        }
    )
