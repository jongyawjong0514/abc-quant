import pandas as pd
import pytest

from abc_quant.data.local_tw_loader import DataQualityReport, LocalTwDataBundle
from abc_quant.features.walkline_features import compute_walkline_features, _cluster_price_zones
from abc_quant.reports.zhu_walkline_report import (
    _candidate_records,
    _risk_records,
    _shadow_log_frame,
    _stock_report,
    _summary_payload,
)
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


def _mock_bundle(price: pd.DataFrame) -> LocalTwDataBundle:
    stock_ids = sorted(price["stock_id"].astype(str).unique())
    quality = DataQualityReport(sqlite_path="mock.sqlite", sqlite_exists=True)
    return LocalTwDataBundle(
        asof_date="2026-06-30",
        requested_asof="2026-06-30",
        price_history=price,
        stock_info=pd.DataFrame(
            {
                "stock_id": stock_ids,
                "stock_name": [f"測試{stock_id}" for stock_id in stock_ids],
                "sector": ["半導體"] * len(stock_ids),
                "market": ["TWSE"] * len(stock_ids),
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
    bundle = _mock_bundle(price)
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
    assert {
        "signal_stage",
        "trigger_type",
        "buy_observation_type",
        "buy_observation_detail_types",
        "buy_trigger_price",
        "buy_trigger_price_role",
        "target_resistance_1",
        "target_resistance_2",
        "sell_warning_type",
        "sell_warning_detail_types",
        "stop_reference",
        "invalidation_price",
        "invalid_price",
        "confirm_price",
        "failure_type",
    }.issubset(result.feature_matrix.columns)


def test_zhu_walkline_mode_is_locked_to_shadow_observation() -> None:
    bundle = _mock_bundle(_mock_price_frame("2330"))
    result = build_zhu_walkline_shadow_result(
        bundle,
        concept_map={"SEMICONDUCTOR": ["2330"]},
        web_records=[],
        top_n=10,
        web_research_used=False,
        config={"project": {"mode": "formal_trade"}, "scoring": {"web_score_cap": 5}},
    )

    assert result.mode == "shadow_observation_only"
    assert any("project.mode=formal_trade ignored" in note for note in result.run_notes)


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


def test_buy_observation_fields_flag_resistance_breakout() -> None:
    frame = _scoring_frame()
    frame.loc[0, "close"] = 105.0
    frame.loc[0, "high"] = 106.0
    frame.loc[0, "breakout_zone_high"] = 102.0
    frame.loc[0, "resistance_zone_breakout_today"] = True
    frame.loc[0, "resistance_zone_1_low"] = 110.0
    frame.loc[0, "resistance_zone_1_high"] = 112.0
    frame.loc[0, "resistance_zone_2_high"] = 120.0
    frame.loc[0, "volume"] = 2000.0
    frame.loc[0, "vol_ma5"] = 1500.0
    frame.loc[0, "vol_ma20"] = 1400.0

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert frame.loc[0, "buy_observation_type"] == "RESISTANCE_BREAKOUT"
    assert "RESISTANCE_BREAKOUT" in frame.loc[0, "buy_observation_detail_types"]
    assert "|" not in frame.loc[0, "buy_observation_type"]
    assert frame.loc[0, "buy_trigger_price"] == pytest.approx(102.0)
    assert frame.loc[0, "buy_trigger_price_role"] == "TRIGGERED_PRICE"
    assert frame.loc[0, "target_resistance_1"] == pytest.approx(112.0)
    assert frame.loc[0, "target_resistance_2"] == pytest.approx(120.0)
    assert frame.loc[0, "invalidation_price"] == pytest.approx(95.0)


def test_resistance_turn_support_requires_prior_breakout_then_retest() -> None:
    frame = _scoring_frame()
    frame.loc[0, "prev_close"] = 104.0
    frame.loc[0, "close"] = 105.0
    frame.loc[0, "low"] = 101.5
    frame.loc[0, "breakout_zone_high"] = 102.0
    frame.loc[0, "resistance_zone_breakout_today"] = False

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert frame.loc[0, "buy_observation_type"] == "RESISTANCE_TURN_SUPPORT"
    assert frame.loc[0, "buy_trigger_price"] == pytest.approx(102.0)


def test_same_day_breakout_is_not_resistance_turn_support() -> None:
    frame = _scoring_frame()
    frame.loc[0, "prev_close"] = 100.0
    frame.loc[0, "close"] = 105.0
    frame.loc[0, "low"] = 101.5
    frame.loc[0, "breakout_zone_high"] = 102.0
    frame.loc[0, "resistance_zone_breakout_today"] = True

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert frame.loc[0, "buy_observation_type"] == "RESISTANCE_BREAKOUT"
    assert "RESISTANCE_TURN_SUPPORT" not in frame.loc[0, "buy_observation_detail_types"]


def test_buy_trigger_price_role_marks_next_confirmation_when_not_triggered() -> None:
    frame = _scoring_frame()
    frame.loc[0, "close"] = 100.0
    frame.loc[0, "close_above_prev_high"] = False
    frame.loc[0, "resistance_zone_breakout_today"] = False
    frame.loc[0, "support_zone_holding_today"] = False
    frame.loc[0, "volume"] = 900.0
    frame.loc[0, "vol_ma5"] = 1200.0
    frame.loc[0, "vol_ma20"] = 1000.0

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert frame.loc[0, "buy_observation_type"] == ""
    assert frame.loc[0, "buy_trigger_price"] == pytest.approx(103.0)
    assert frame.loc[0, "buy_trigger_price_role"] == "NEXT_CONFIRMATION_PRICE"


def test_sell_warning_fields_flag_breakdown_false_breakout_and_ma_failure() -> None:
    frame = _scoring_frame()
    frame.loc[0, "close"] = 93.0
    frame.loc[0, "high"] = 106.0
    frame.loc[0, "support_zone_failed_today"] = True
    frame.loc[0, "close_below_prev_low"] = True
    frame.loc[0, "price_down_volume_up"] = True
    frame.loc[0, "resistance_zone_breakout_failed_today"] = True
    frame.loc[0, "high_volume_red_k_low"] = 96.0
    frame.loc[0, "ma_break_5"] = True
    frame.loc[0, "ma_state"] = "MA_BREAK"

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert frame.loc[0, "sell_warning_type"] == "SUPPORT_BREAKDOWN"
    assert "|" not in frame.loc[0, "sell_warning_type"]
    sell_warning_detail_types = frame.loc[0, "sell_warning_detail_types"]
    assert "SUPPORT_BREAKDOWN" in sell_warning_detail_types
    assert "FALSE_BREAKOUT" in sell_warning_detail_types
    assert "ATTACK_K_FAILURE" in sell_warning_detail_types
    assert "MA_SUPPORT_FAILURE" in sell_warning_detail_types


def test_price_down_volume_up_alone_does_not_mark_support_breakdown() -> None:
    frame = _scoring_frame()
    frame.loc[0, "close"] = 100.0
    frame.loc[0, "support_zone_failed_today"] = True
    frame.loc[0, "price_down_volume_up"] = True
    frame.loc[0, "close_below_prev_low"] = False
    frame.loc[0, "broken_support_zone_low"] = pd.NA

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert frame.loc[0, "sell_warning_type"] != "SUPPORT_BREAKDOWN"
    assert "SUPPORT_BREAKDOWN" not in frame.loc[0, "sell_warning_detail_types"]


def test_target_resistance_must_be_above_close() -> None:
    frame = _scoring_frame()
    frame.loc[0, "close"] = 105.0
    frame.loc[0, "resistance_zone_1_high"] = 103.0
    frame.loc[0, "resistance_1"] = 104.0
    frame.loc[0, "prev_high"] = 104.5
    frame.loc[0, "resistance_zone_2_high"] = 104.0
    frame.loc[0, "resistance_2"] = 104.5
    frame.loc[0, "high_20d"] = 104.9
    frame.loc[0, "high_60d"] = 104.9

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    assert pd.isna(frame.loc[0, "target_resistance_1"])
    assert pd.isna(frame.loc[0, "target_resistance_2"])


def test_missing_price_fields_do_not_emit_nan_like_strings() -> None:
    frame = _scoring_frame()
    for column in [
        "support_zone_1_low",
        "support_1",
        "ma20",
        "prev_low",
        "resistance_zone_1_high",
        "resistance_1",
        "prev_high",
        "ma5",
        "stop_reference",
    ]:
        frame.loc[0, column] = pd.NA

    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )
    log_frame = _shadow_log_frame(frame)

    assert pd.isna(frame.loc[0, "invalid_price"])
    assert pd.isna(frame.loc[0, "confirm_price"])
    assert not log_frame.map(lambda value: str(value).lower() in {"nan", "none", "<na>"}).any().any()


def test_summary_records_include_stop_reference_and_detail_fields() -> None:
    frame = _scoring_frame()
    _score_features(
        frame,
        market={"market_state": "MARKET_RANGE_BOUND", "market_score": 4, "market_risk_score": 4},
        config={"scoring": {"web_score_cap": 5}},
    )

    candidate = _candidate_records(frame)[0]
    risk = _risk_records(frame)[0]

    assert "stop_reference" in candidate
    assert "stop_reference" in risk
    assert "buy_observation_detail_types" in candidate
    assert "buy_trigger_price_role" in candidate
    assert "sell_warning_detail_types" in candidate
    assert "sell_warning_detail_types" in risk


def test_reports_use_observation_language_not_trade_commands() -> None:
    result = build_zhu_walkline_shadow_result(
        _mock_bundle(_mock_price_frame("2330")),
        concept_map={"SEMICONDUCTOR": ["2330"]},
        web_records=[],
        top_n=5,
        web_research_used=False,
        config={"scoring": {"web_score_cap": 5}},
    )
    payload = _summary_payload(result, DataQualityReport(sqlite_path="mock.sqlite", sqlite_exists=True))
    report = _stock_report(result)

    assert "不是買進名單，不是賣出指令，僅為支撐壓力觀察價與訊號失效價。" in report
    assert "NEXT_CONFIRMATION_PRICE" in report or "TRIGGERED_PRICE" in report or "EMPTY" in report
    banned_phrases = ["續" + "抱條件", "減" + "碼條件", "停" + "損條件", "降低" + "部位"]
    for banned in banned_phrases:
        assert banned not in report
    assert payload["mode"] == "shadow_observation_only"



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
            "open": [97.0],
            "high": [101.0],
            "low": [96.0],
            "close": [100.0],
            "prev_close": [97.0],
            "volume": [1600.0],
            "vol_ma5": [1200.0],
            "vol_ma20": [1000.0],
            "ma5": [98.0],
            "ma10": [97.0],
            "ma20": [95.0],
            "prev_high": [99.0],
            "prev_low": [94.0],
            "support_1": [95.0],
            "support_2": [90.0],
            "resistance_1": [102.0],
            "resistance_2": [110.0],
            "support_zone_1_low": [95.0],
            "support_zone_1_high": [96.0],
            "support_zone_1_label": ["95.00~96.00"],
            "support_zone_2_low": [90.0],
            "support_zone_2_high": [91.0],
            "resistance_zone_1_low": [102.0],
            "resistance_zone_1_high": [103.0],
            "resistance_zone_1_label": ["102.00~103.00"],
            "resistance_zone_2_low": [110.0],
            "resistance_zone_2_high": [111.0],
            "high_20d": [111.0],
            "high_60d": [115.0],
            "broken_support_zone_low": [pd.NA],
            "broken_support_zone_high": [pd.NA],
            "breakout_zone_low": [pd.NA],
            "breakout_zone_high": [pd.NA],
            "distance_to_60d_high": [0.1],
            "vol_ratio_20": [1.6],
            "upper_shadow_pct": [0.01],
            "lower_shadow_pct": [0.02],
            "close_position_in_range": [0.9],
            "institutional_total_buy_sell": [0.0],
            "black_k": [False],
            "return_1d": [0.03],
            "support_broken_today": [False],
            "support_zone_holding_today": [False],
            "support_zone_failed_today": [False],
            "resistance_zone_breakout_today": [False],
            "resistance_zone_breakout_failed_today": [False],
            "margin_change_1d": [0.0],
            "margin_consecutive_increase_days": [0.0],
            "close_above_prev_high": [True],
            "close_above_ma5": [True],
            "volume_expansion": [True],
            "ma_reclaim_20": [False],
            "ma_reclaim_10": [False],
            "ma_reclaim_5": [False],
            "ma_break_5": [False],
            "ma_break_10": [False],
            "ma_break_20": [False],
            "hammer_like": [False],
            "shooting_star_like": [False],
            "red_k": [True],
            "failed_breakdown": [False],
            "break_prev_low": [False],
            "close_below_prev_low": [False],
            "price_down_volume_up": [False],
            "trend_state": ["UPTREND"],
            "low_volume_pullback": [False],
            "failed_breakout": [False],
            "high_volume_red_k_low": [pd.NA],
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
            "stop_reference": ["跌破支撐區 95.00~96.00 重新評估"],
        }
    )
