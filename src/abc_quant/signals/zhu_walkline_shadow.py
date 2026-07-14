"""Shadow advisory walkline signal builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from abc_quant.data.local_tw_loader import LocalTwDataBundle
from abc_quant.features.chip_features import compute_big_holder_features, compute_chip_features
from abc_quant.features.margin_features import compute_margin_features
from abc_quant.features.market_rotation import (
    classify_market_state,
    compute_concept_rotation,
    compute_sector_rotation,
)
from abc_quant.features.news_event_features import compute_news_event_features
from abc_quant.features.walkline_features import (
    compute_walkline_features,
    forbidden_signal_feature_columns,
)

SHADOW_OBSERVATION_MODE = "shadow_observation_only"
BUY_OBSERVATION_PRIORITY = (
    "RESISTANCE_BREAKOUT",
    "RESISTANCE_TURN_SUPPORT",
    "FAILED_BREAKDOWN_RECLAIM",
    "SUPPORT_REBOUND",
    "KD_OVERSOLD_TREND_RECOVERY",
)
SELL_WARNING_PRIORITY = (
    "SUPPORT_BREAKDOWN",
    "FALSE_BREAKOUT",
    "ATTACK_K_FAILURE",
    "MA_SUPPORT_FAILURE",
    "RESISTANCE_REJECTION",
)
RETEST_TOLERANCE_PCT = 0.015


@dataclass(frozen=True)
class ZhuWalklineResult:
    asof_date: str
    mode: str
    formal_champion_changed: bool
    formal_trade_effect: bool
    web_research_used: bool
    web_research_is_supplementary: bool
    feature_matrix: pd.DataFrame
    top_bullish_watchlist: pd.DataFrame
    top_rise_candidates: pd.DataFrame
    top_fall_risks: pd.DataFrame
    market: dict[str, Any]
    sector_rotation: pd.DataFrame
    concept_rotation: pd.DataFrame
    web_records: list[dict[str, Any]]
    run_notes: list[str]


def build_zhu_walkline_shadow_result(
    bundle: LocalTwDataBundle,
    *,
    concept_map: dict[str, list[str]],
    web_records: list[dict[str, Any]],
    top_n: int,
    web_research_used: bool,
    config: dict[str, Any],
) -> ZhuWalklineResult:
    """Build the full shadow advisory result from local as-of data."""
    walkline = compute_walkline_features(bundle.price_history, asof_date=bundle.asof_date)
    market = classify_market_state(
        bundle.market_history,
        bundle.price_history,
        asof_date=bundle.asof_date,
    )
    sector_rotation, sector_context = compute_sector_rotation(
        walkline,
        bundle.stock_info,
        bundle.sector_sentiment,
    )
    concept_rotation, concept_context = compute_concept_rotation(walkline, concept_map)
    chip = compute_chip_features(bundle.chip_history, asof_date=bundle.asof_date)
    holder = compute_big_holder_features(
        _filter_snapshot_asof(bundle.holder_latest, date_column="date", asof_date=bundle.asof_date),
        walkline,
    )
    margin = compute_margin_features(bundle.margin_history, walkline, asof_date=bundle.asof_date)
    news = compute_news_event_features(
        web_records,
        asof_date=bundle.asof_date,
        web_score_cap=float(config.get("scoring", {}).get("web_score_cap", 5)),
    )

    features = _merge_feature_layers(
        walkline=walkline,
        stock_info=bundle.stock_info,
        sector_context=sector_context,
        concept_context=concept_context,
        chip=chip,
        holder=holder,
        margin=margin,
        news=news,
        market=market,
    )
    forbidden = forbidden_signal_feature_columns(features.columns)
    if forbidden:
        raise ValueError("signal feature matrix contains forbidden future/label columns: " + ", ".join(forbidden))
    _score_features(features, market=market, config=config)
    top_bullish = features[features["grade"] != ""].sort_values(
        ["rise_score", "fall_risk_score"], ascending=[False, True]
    ).head(top_n)
    top_fall = features[features["risk_grade"] != ""].sort_values(
        ["fall_risk_score", "rise_score"], ascending=[False, True]
    ).head(top_n)
    run_notes = list(bundle.data_quality.warnings)
    configured_mode = str(config.get("project", {}).get("mode", SHADOW_OBSERVATION_MODE))
    if configured_mode != SHADOW_OBSERVATION_MODE:
        run_notes.append(
            f"project.mode={configured_mode} ignored; Zhu walkline scanner is locked to "
            f"{SHADOW_OBSERVATION_MODE}."
        )
    if not web_research_used:
        run_notes.append("未啟用或無法使用網路搜尋，本次分析僅使用本地資料庫。")
    return ZhuWalklineResult(
        asof_date=bundle.asof_date,
        mode=SHADOW_OBSERVATION_MODE,
        formal_champion_changed=False,
        formal_trade_effect=False,
        web_research_used=web_research_used,
        web_research_is_supplementary=True,
        feature_matrix=features,
        top_bullish_watchlist=top_bullish,
        top_rise_candidates=top_bullish,
        top_fall_risks=top_fall,
        market=market,
        sector_rotation=sector_rotation,
        concept_rotation=concept_rotation,
        web_records=web_records,
        run_notes=run_notes,
    )


def compute_forward_evaluation(
    result: ZhuWalklineResult,
    future_prices: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluator-only forward returns. These columns never enter features."""
    selected = pd.concat(
        [
            result.top_rise_candidates.assign(candidate_side="rise"),
            result.top_fall_risks.assign(candidate_side="fall"),
        ],
        ignore_index=True,
    )
    if selected.empty or future_prices.empty:
        return pd.DataFrame(), {
            "asof_date": result.asof_date,
            "note": "no evaluator rows available after asof_date",
        }
    future = future_prices.copy()
    future["date"] = pd.to_datetime(future["date"], errors="raise")
    future = future.sort_values(["stock_id", "date"])
    rows: list[dict[str, Any]] = []
    for _, stock in selected.drop_duplicates(["stock_id", "candidate_side"]).iterrows():
        stock_future = future[future["stock_id"] == stock["stock_id"]].reset_index(drop=True)
        row = {
            "asof_date": result.asof_date,
            "stock_id": stock["stock_id"],
            "stock_name": stock.get("stock_name", ""),
            "candidate_side": stock["candidate_side"],
            "asof_close": stock["close"],
        }
        for horizon in (1, 3, 5, 10):
            value = np.nan
            hit: object = pd.NA
            if len(stock_future) >= horizon:
                value = float(stock_future.loc[horizon - 1, "close"] / stock["close"] - 1.0)
                hit = bool(value > 0) if stock["candidate_side"] == "rise" else bool(value < 0)
            row[f"future_return_d{horizon}"] = value
            row[f"hit_d{horizon}"] = hit
        first5 = stock_future.head(5)
        row["max_drawdown_next_5d"] = (
            float(first5["low"].min() / stock["close"] - 1.0) if not first5.empty else np.nan
        )
        row["max_gain_next_5d"] = (
            float(first5["high"].max() / stock["close"] - 1.0) if not first5.empty else np.nan
        )
        rows.append(row)
    frame = pd.DataFrame(rows)
    summary = {
        "asof_date": result.asof_date,
        "note": "離線評估，不可用於當日訊號",
        "rise_candidate_d1_hit_rate": _hit_rate(frame, "rise", "hit_d1"),
        "rise_candidate_d3_hit_rate": _hit_rate(frame, "rise", "hit_d3"),
        "rise_candidate_d5_hit_rate": _hit_rate(frame, "rise", "hit_d5"),
        "fall_risk_d1_hit_rate": _hit_rate(frame, "fall", "hit_d1"),
        "fall_risk_d3_hit_rate": _hit_rate(frame, "fall", "hit_d3"),
        "fall_risk_d5_hit_rate": _hit_rate(frame, "fall", "hit_d5"),
        "avg_forward_return_d1": _mean(frame, "future_return_d1"),
        "avg_forward_return_d3": _mean(frame, "future_return_d3"),
        "avg_forward_return_d5": _mean(frame, "future_return_d5"),
        "max_drawdown_next_5d": _mean(frame, "max_drawdown_next_5d"),
        "precision_at_10": _precision_at(frame, 10),
        "precision_at_30": _precision_at(frame, 30),
    }
    return frame, summary


def _merge_feature_layers(
    *,
    walkline: pd.DataFrame,
    stock_info: pd.DataFrame,
    sector_context: pd.DataFrame,
    concept_context: pd.DataFrame,
    chip: pd.DataFrame,
    holder: pd.DataFrame,
    margin: pd.DataFrame,
    news: pd.DataFrame,
    market: dict[str, Any],
) -> pd.DataFrame:
    features = walkline.copy()
    if not stock_info.empty:
        features = features.merge(stock_info, on="stock_id", how="left")
    if "stock_name" not in features.columns:
        features["stock_name"] = ""
    features["stock_name"] = features["stock_name"].fillna("")
    if "sector" not in features.columns:
        features["sector"] = "UNKNOWN"
    features["sector"] = features["sector"].fillna("UNKNOWN")
    for frame in [sector_context, concept_context, chip, holder, margin, news]:
        if frame is not None and not frame.empty:
            features = features.merge(frame, on="stock_id", how="left", suffixes=("", "_dup"))
            duplicate_cols = [col for col in features.columns if col.endswith("_dup")]
            if duplicate_cols:
                features = features.drop(columns=duplicate_cols)
    features["concepts"] = features.get("concepts", pd.Series([[]] * len(features), index=features.index))
    features["concepts"] = features["concepts"].map(lambda value: value if isinstance(value, list) else [])
    features["market_state"] = market["market_state"]
    features = _fill_defaults(features)
    return features


def _filter_snapshot_asof(frame: pd.DataFrame, *, date_column: str, asof_date: str) -> pd.DataFrame:
    if frame.empty or date_column not in frame.columns:
        return frame
    data = frame.copy()
    data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
    data = data[data[date_column] <= pd.to_datetime(asof_date)].copy()
    if data.empty:
        return data
    if "stock_id" in data.columns:
        data["stock_id"] = data["stock_id"].astype(str)
        return data.sort_values(["stock_id", date_column]).groupby("stock_id", sort=False).tail(1)
    return data.sort_values(date_column).tail(1)


def _fill_defaults(features: pd.DataFrame) -> pd.DataFrame:
    numeric_defaults = {
        "sector_rotation_rank": 999,
        "sector_strength_score": 0.0,
        "sector_risk_score": 50.0,
        "concept_rotation_rank": 999,
        "concept_strength_score": 0.0,
        "concept_risk_score": 50.0,
        "institutional_score": 0.0,
        "institutional_selling_score": 0.0,
        "foreign_5d": 0.0,
        "investment_trust_5d": 0.0,
        "dealer_5d": 0.0,
        "big_holder_score": 0.0,
        "margin_score": 0.0,
        "margin_risk_score": 0.0,
        "event_score_for_rise": 0.0,
        "event_score_for_fall": 0.0,
        "supply_pressure_score": 0.0,
        "institutional_total_buy_sell": 0.0,
        "margin_change_1d": 0.0,
        "margin_consecutive_increase_days": 0.0,
    }
    for column, default in numeric_defaults.items():
        if column not in features.columns:
            features[column] = default
        features[column] = pd.to_numeric(features[column], errors="coerce").fillna(default)
    for column in ["sector_state", "big_holder_data_source"]:
        if column not in features.columns:
            features[column] = ""
        features[column] = features[column].fillna("")
    return features


def _score_features(features: pd.DataFrame, *, market: dict[str, Any], config: dict[str, Any]) -> None:
    scoring = config.get("scoring", {})
    market_state = str(market["market_state"])
    features["market_state"] = market_state
    features["market_score_component"] = float(market.get("market_score", 0))
    features["market_risk_score_component"] = float(market.get("market_risk_score", 0)) * 1.5
    features["sector_rotation_score"] = (features["sector_strength_score"] * 0.15).clip(0, 15)
    features["concept_rotation_score"] = (features["concept_strength_score"] * 0.10).clip(0, 10)
    features["sector_weakness_score"] = (features["sector_risk_score"] * 0.15).clip(0, 15)
    features["concept_weakness_score"] = (features["concept_risk_score"] * 0.10).clip(0, 10)
    features["trend_score"] = features["trend_state"].map(
        {
            "UPTREND": 15,
            "PULLBACK_IN_UPTREND": 10,
            "RANGE_BOUND": 5,
            "WEAK_REBOUND": 3,
            "DOWNTREND": 0,
            "BREAKDOWN": 0,
        }
    ).fillna(0)
    features["ma_score"] = features["ma_state"].map(
        {
            "BULL_ALIGNMENT": 15,
            "MA_RECLAIM": 12,
            "BULL_PULLBACK": 8,
            "MA_COMPRESSION": 5,
            "MA_BREAK": 1,
            "BEAR_ALIGNMENT": 0,
        }
    ).fillna(0)
    features["kline_score"] = features["kline_state"].map(
        {
            "ATTACK_RED_K": 10,
            "STOPPING_K": 6,
            "WEAK_REBOUND_K": 3,
            "RANGE_K": 2,
            "UPPER_SHADOW_SUPPLY": 0,
            "LONG_BLACK_K": 0,
            "BREAKDOWN_K": 0,
        }
    ).fillna(0)
    features["volume_score"] = features["volume_state"].map(
        {
            "ATTACK_VOLUME": 10,
            "HEALTHY_PULLBACK_VOLUME": 8,
            "NEUTRAL_VOLUME": 4,
            "WEAK_REBOUND_VOLUME": 2,
            "DISTRIBUTION_VOLUME": 0,
            "PANIC_VOLUME": 0,
        }
    ).fillna(0)
    _add_signal_stage_and_failure_fields(features, market_state=market_state)
    features["risk_penalty"] = (
        features["support_broken_today"].astype(float) * 8
        + features["high_volume_upper_shadow"].astype(float) * 6
        + features["supply_pressure_score"].fillna(0)
        + features["margin_risk_score"].fillna(0) * 0.6
    )
    if market_state == "MARKET_HIGH_RISK_BREAKDOWN":
        features["risk_penalty"] += 20
    elif market_state == "MARKET_DOWNTREND":
        features["risk_penalty"] += 10
    elif market_state == "MARKET_WEAK_REBOUND":
        features["risk_penalty"] += 5

    features["rise_score"] = (
        features["market_score_component"]
        + features["sector_rotation_score"]
        + features["concept_rotation_score"]
        + features["trend_score"]
        + features["ma_score"]
        + features["kline_score"]
        + features["volume_score"]
        + features["institutional_score"].clip(0, 10)
        + features["big_holder_score"].clip(0, 5)
        + features["margin_score"].clip(0, 5)
        + features["event_score_for_rise"].clip(0, float(scoring.get("web_score_cap", 5)))
        - features["risk_penalty"].clip(0, 30)
    ).clip(0, 100)
    features["web_event_score"] = features["event_score_for_rise"].clip(
        0, float(scoring.get("web_score_cap", 5))
    )

    features["trend_break_score"] = features["trend_state"].map(
        {"BREAKDOWN": 15, "DOWNTREND": 12, "WEAK_REBOUND": 8, "RANGE_BOUND": 4}
    ).fillna(0)
    features["ma_break_score"] = features["ma_state"].map(
        {"BEAR_ALIGNMENT": 15, "MA_BREAK": 12, "MA_COMPRESSION": 4}
    ).fillna(0)
    features["kline_weakness_score"] = features["kline_state"].map(
        {"BREAKDOWN_K": 10, "LONG_BLACK_K": 10, "UPPER_SHADOW_SUPPLY": 8, "WEAK_REBOUND_K": 5}
    ).fillna(0)
    features["volume_distribution_score"] = features["volume_state"].map(
        {"DISTRIBUTION_VOLUME": 10, "PANIC_VOLUME": 8, "WEAK_REBOUND_VOLUME": 4}
    ).fillna(0)
    features["support_break_penalty"] = features["support_broken_today"].astype(float) * 10
    features["fall_risk_score"] = (
        features["market_risk_score_component"].clip(0, 15)
        + features["sector_weakness_score"]
        + features["concept_weakness_score"]
        + features["trend_break_score"]
        + features["ma_break_score"]
        + features["kline_weakness_score"]
        + features["volume_distribution_score"]
        + features["institutional_selling_score"].clip(0, 10)
        + features["margin_risk_score"].clip(0, 10)
        + features["support_break_penalty"]
        + features["event_score_for_fall"].clip(0, float(scoring.get("web_score_cap", 5)))
    ).clip(0, 100)
    features["web_event_risk_score"] = features["event_score_for_fall"].clip(
        0, float(scoring.get("web_score_cap", 5))
    )

    features["grade"] = np.select(
        [
            features["rise_score"] >= float(scoring.get("rise_min_a", 80)),
            features["rise_score"] >= float(scoring.get("rise_min_b", 70)),
            features["rise_score"] >= float(scoring.get("rise_min_c", 60)),
        ],
        ["A", "B", "C"],
        default="",
    )
    features["grade"] = features.apply(_apply_market_grade_cap, axis=1)
    features["risk_grade"] = np.select(
        [
            features["fall_risk_score"] >= float(scoring.get("fall_high", 80)),
            features["fall_risk_score"] >= float(scoring.get("fall_medium", 65)),
            features["fall_risk_score"] >= float(scoring.get("fall_watch", 50)),
        ],
        ["HIGH_RISK", "MEDIUM_RISK", "WATCH_RISK"],
        default="",
    )
    features["reason"] = features.apply(_rise_reasons, axis=1)
    features["risk_reason"] = features.apply(_risk_reasons, axis=1)
    features["reason_summary"] = features["reason"].map("; ".join)
    features["risk_reason_summary"] = features["risk_reason"].map("; ".join)
    features["trend_break_reason"] = features["trend_state"].map(str)
    features["ma_break_reason"] = features["ma_state"].map(str)
    features["kline_weakness"] = features["kline_state"].map(str)
    features["volume_distribution"] = features["volume_state"].map(str)
    features["institutional_selling"] = features["institutional_selling_score"].map(lambda v: f"{v:.1f}")
    features["margin_risk"] = features["margin_risk_score"].map(lambda v: f"{v:.1f}")
    features["support_broken"] = features.apply(
        lambda row: [_zone_label(row, "broken_support_zone")]
        if bool(row.get("support_zone_failed_today", False))
        and pd.notna(row.get("broken_support_zone_low"))
        else (
            [_zone_label(row, "support_zone_1")]
            if bool(row["support_broken_today"]) and pd.notna(row.get("support_zone_1_low"))
            else []
        ),
        axis=1,
    )
    features["next_support"] = features.apply(
        lambda row: [
            _zone_label(row, prefix)
            for prefix in ["support_zone_1", "support_zone_2"]
            if pd.notna(row.get(f"{prefix}_low"))
        ],
        axis=1,
    )


def _rise_reasons(row: pd.Series) -> list[str]:
    reasons: list[str] = []
    if row["trend_state"] in {"UPTREND", "PULLBACK_IN_UPTREND"}:
        reasons.append(f"趨勢={row['trend_state']}")
    if row["ma_state"] in {"BULL_ALIGNMENT", "MA_RECLAIM"}:
        reasons.append(f"均線={row['ma_state']}")
    if row["kline_state"] == "ATTACK_RED_K":
        reasons.append("攻擊K收過前高")
    if row["volume_state"] in {"ATTACK_VOLUME", "HEALTHY_PULLBACK_VOLUME"}:
        reasons.append(f"量能={row['volume_state']}")
    if row["institutional_score"] > 0:
        reasons.append("法人籌碼加分")
    if row["big_holder_score"] > 0:
        reasons.append("大戶/主力proxy加分")
    if row["margin_score"] > 0:
        reasons.append("融資結構較乾淨")
    if row.get("signal_stage"):
        reasons.append(f"訊號階段={row['signal_stage']}")
    if row.get("trigger_type"):
        reasons.append(f"觸發={row['trigger_type']}")
    if bool(row.get("kd_recovery_confirmation", False)):
        reasons.append(
            "KD超賣後確認：前5日有窄幅縮量、K上彎突破D、價格站回壓力且通過多頭強勢閘門"
        )
    elif bool(row.get("kd_oversold_marker", False)):
        reasons.append("KD短線超賣僅為標記，尚未止跌")
    if not reasons:
        reasons.append("訊號不足，僅列觀察")
    return reasons


def _risk_reasons(row: pd.Series) -> list[str]:
    reasons: list[str] = []
    if row["trend_state"] in {"DOWNTREND", "BREAKDOWN"}:
        reasons.append(f"趨勢轉弱={row['trend_state']}")
    if row["ma_state"] in {"MA_BREAK", "BEAR_ALIGNMENT"}:
        reasons.append(f"均線轉弱={row['ma_state']}")
    if row["kline_state"] in {"LONG_BLACK_K", "UPPER_SHADOW_SUPPLY", "BREAKDOWN_K"}:
        reasons.append(f"K棒風險={row['kline_state']}")
    if row["volume_state"] in {"DISTRIBUTION_VOLUME", "PANIC_VOLUME"}:
        reasons.append(f"量能風險={row['volume_state']}")
    if row["institutional_selling_score"] > 0:
        reasons.append("法人賣壓")
    if row["margin_risk_score"] > 0:
        reasons.append("融資風險")
    if bool(row.get("support_broken_today", False)):
        reasons.append("跌破支撐或20日線")
    if row.get("failure_type"):
        reasons.append(f"失敗型態={row['failure_type']}")
    if not reasons:
        reasons.append("未達明顯風險條件")
    return reasons


def _add_signal_stage_and_failure_fields(features: pd.DataFrame, *, market_state: str) -> None:
    """Add signal lifecycle fields and hard-risk labels."""
    features["high_level_supply_pressure"] = (
        (features["distance_to_60d_high"].fillna(1.0) <= 0.05)
        & (features["vol_ratio_20"].fillna(0.0) >= 1.5)
        & (features["upper_shadow_pct"].fillna(0.0) >= 0.025)
        & (features["close_position_in_range"].fillna(0.5) < 0.65)
    )
    features["supply_pressure_score"] = np.maximum(
        features["supply_pressure_score"].fillna(0.0),
        features["high_level_supply_pressure"].astype(float) * 8.0,
    )
    features["institutional_divergence"] = (
        (features["institutional_total_buy_sell"].fillna(0.0) > 0)
        & (features["black_k"].fillna(False) | (features["return_1d"].fillna(0.0) <= 0))
    )
    features["institutional_support"] = (
        (features["institutional_total_buy_sell"].fillna(0.0) < 0)
        & (features["return_1d"].fillna(0.0) >= 0)
    )
    close_numeric = pd.to_numeric(features["close"], errors="coerce")
    ma20_numeric = pd.to_numeric(features["ma20"], errors="coerce")
    features["margin_crowding_risk"] = (
        ((close_numeric < ma20_numeric).fillna(False) | features["support_broken_today"].fillna(False))
        & (
            (features["margin_change_1d"].fillna(0.0) > 0)
            | (features["margin_consecutive_increase_days"].fillna(0.0) > 0)
        )
    )
    features["reversal_state"] = features.apply(_reversal_state, axis=1)
    features["trigger_type"] = features.apply(_trigger_type, axis=1)
    features["failure_type"] = features.apply(
        lambda row: "|".join(_failure_types(row, market_state=market_state)),
        axis=1,
    )
    features["signal_stage"] = features.apply(_signal_stage, axis=1)
    features["invalid_price"] = features.apply(_invalid_price, axis=1)
    features["confirm_price"] = features.apply(_confirm_price, axis=1)
    features["buy_observation_detail_types"] = features.apply(
        lambda row: "|".join(_buy_observation_types(row)),
        axis=1,
    )
    features["buy_observation_type"] = features["buy_observation_detail_types"].map(
        lambda value: _primary_type(value, BUY_OBSERVATION_PRIORITY)
    )
    features["buy_trigger_price"] = features.apply(_buy_trigger_price, axis=1)
    features["buy_trigger_price_role"] = features.apply(_buy_trigger_price_role, axis=1)
    features["target_resistance_1"] = features.apply(
        lambda row: _target_resistance(
            row,
            ("resistance_zone_1_high", "resistance_1", "prev_high", "high_20d"),
        ),
        axis=1,
    )
    features["target_resistance_2"] = features.apply(
        lambda row: _target_resistance(
            row,
            ("resistance_zone_2_high", "resistance_2", "high_60d", "high_20d"),
        ),
        axis=1,
    )
    features["sell_warning_detail_types"] = features.apply(
        lambda row: "|".join(_sell_warning_types(row)),
        axis=1,
    )
    features["sell_warning_type"] = features["sell_warning_detail_types"].map(
        lambda value: _primary_type(value, SELL_WARNING_PRIORITY)
    )
    features["invalidation_price"] = features["invalid_price"]
    features["non_holder_observation"] = features.apply(_non_holder_observation, axis=1)
    features["holder_discipline"] = features.apply(_holder_discipline, axis=1)


def _reversal_state(row: pd.Series) -> str:
    if bool(row.get("kd_recovery_confirmation", False)):
        return "confirmed_reversal"
    if bool(row.get("close_above_prev_high", False)) and bool(row.get("close_above_ma5", False)) and bool(row.get("volume_expansion", False)):
        return "confirmed_reversal"
    if bool(row.get("hammer_like", False)) or bool(row.get("red_k", False)) or bool(row.get("failed_breakdown", False)):
        return "reversal_attempt"
    if row.get("trend_state") == "WEAK_REBOUND" or (row.get("return_1d", 0.0) > 0 and not bool(row.get("close_above_ma5", False))):
        return "weak_rebound"
    return "none"


def _trigger_type(row: pd.Series) -> str:
    if bool(row.get("kd_recovery_confirmation", False)):
        return "KD_OVERSOLD_RECOVERY"
    if bool(row.get("close_above_prev_high", False)) and bool(row.get("close_above_ma5", False)) and bool(row.get("volume_expansion", False)):
        return "RANGE_BREAKOUT"
    if bool(row.get("ma_reclaim_20", False)) or bool(row.get("ma_reclaim_10", False)) or bool(row.get("ma_reclaim_5", False)):
        return "MA_RECLAIM"
    if bool(row.get("close_above_prev_high", False)):
        return "BREAK_PREV_HIGH"
    if row.get("reversal_state") == "confirmed_reversal":
        return "BOTTOM_REVERSAL"
    if row.get("trend_state") == "PULLBACK_IN_UPTREND" and bool(row.get("low_volume_pullback", False)):
        return "PULLBACK_RESTART"
    return ""


def _failure_types(row: pd.Series, *, market_state: str) -> list[str]:
    failures: list[str] = []
    if bool(row.get("failed_breakout", False)) or bool(
        row.get("resistance_zone_breakout_failed_today", False)
    ):
        failures.append("FALSE_BREAKOUT")
    if row.get("trigger_type") and not bool(row.get("volume_expansion", False)):
        failures.append("NO_VOLUME_FOLLOW")
    if market_state in {"MARKET_WEAK_REBOUND", "MARKET_DOWNTREND", "MARKET_HIGH_RISK_BREAKDOWN"}:
        failures.append("MARKET_DRAG")
    if row.get("sector_state") in {"SECTOR_ROTATING_OUT", "SECTOR_WEAK"} or row.get("sector_risk_score", 0.0) >= 60:
        failures.append("SECTOR_ROTATION_OUT")
    if bool(row.get("institutional_divergence", False)):
        failures.append("INSTITUTIONAL_DIVERGENCE")
    if bool(row.get("margin_crowding_risk", False)):
        failures.append("MARGIN_CROWDING")
    if bool(row.get("high_level_supply_pressure", False)) or row.get("supply_pressure_score", 0.0) >= 8:
        failures.append("SUPPLY_PRESSURE")
    if _support_breakdown_warning(row):
        failures.append("SUPPORT_BREAK")
    return failures


def _buy_observation_types(row: pd.Series) -> list[str]:
    observations: list[str] = []
    if _resistance_breakout_observation(row):
        observations.append("RESISTANCE_BREAKOUT")
    if _resistance_turn_support_observation(row):
        observations.append("RESISTANCE_TURN_SUPPORT")
    if _failed_breakdown_reclaim_observation(row):
        observations.append("FAILED_BREAKDOWN_RECLAIM")
    if _support_rebound_observation(row):
        observations.append("SUPPORT_REBOUND")
    if _kd_oversold_recovery_observation(row):
        observations.append("KD_OVERSOLD_TREND_RECOVERY")
    return [signal for signal in BUY_OBSERVATION_PRIORITY if signal in set(observations)]


def _buy_trigger_price(row: pd.Series) -> float | None:
    detail_types = set(_split_types(row.get("buy_observation_detail_types", "")))
    triggered_prices: list[float] = []
    if "RESISTANCE_BREAKOUT" in detail_types:
        triggered_prices.append(_first_price(row, ("breakout_zone_high", "resistance_zone_1_high")) or np.nan)
    if "RESISTANCE_TURN_SUPPORT" in detail_types:
        triggered_prices.append(_first_price(row, ("breakout_zone_high", "support_zone_1_high")) or np.nan)
    if "FAILED_BREAKDOWN_RECLAIM" in detail_types:
        triggered_prices.append(_first_price(row, ("prev_low", "broken_support_zone_high")) or np.nan)
    if "SUPPORT_REBOUND" in detail_types:
        triggered_prices.append(_first_price(row, ("prev_high", "resistance_zone_1_high")) or np.nan)
    if "KD_OVERSOLD_TREND_RECOVERY" in detail_types:
        triggered_prices.append(
            _first_price(row, ("kd_reclaim_price", "prev_high", "ma20")) or np.nan
        )
    valid_triggered = [price for price in triggered_prices if _is_finite_price(price)]
    if valid_triggered:
        return float(max(valid_triggered))
    return _first_price(
        row,
        (
            "confirm_price",
            "resistance_zone_1_high",
            "resistance_1",
            "prev_high",
            "ma5",
        ),
    )


def _buy_trigger_price_role(row: pd.Series) -> str:
    trigger_price = row.get("buy_trigger_price")
    if not _is_finite_price(trigger_price):
        return "EMPTY"
    if str(row.get("buy_observation_type", "") or "").strip():
        return "TRIGGERED_PRICE"
    return "NEXT_CONFIRMATION_PRICE"


def _sell_warning_types(row: pd.Series) -> list[str]:
    warnings: list[str] = []
    close = _first_price(row, ("close",))
    if _support_breakdown_warning(row):
        warnings.append("SUPPORT_BREAKDOWN")
    attack_low = _first_price(row, ("high_volume_red_k_low",))
    if _is_finite_price(close) and _is_finite_price(attack_low) and close < attack_low:
        warnings.append("ATTACK_K_FAILURE")
    if bool(row.get("resistance_zone_breakout_failed_today", False)) or bool(
        row.get("failed_breakout", False)
    ):
        warnings.append("FALSE_BREAKOUT")
    resistance_low = _first_price(row, ("resistance_zone_1_low", "resistance_1"))
    resistance_high = _first_price(row, ("resistance_zone_1_high", "resistance_1"))
    high = _first_price(row, ("high",))
    rejection_shape = bool(row.get("shooting_star_like", False)) or bool(
        row.get("high_volume_upper_shadow", False)
    )
    if (
        _is_finite_price(high)
        and _is_finite_price(close)
        and _is_finite_price(resistance_low)
        and _is_finite_price(resistance_high)
        and high >= resistance_low
        and close < resistance_high
        and (rejection_shape or _effective_sell_warning_condition(row))
    ):
        warnings.append("RESISTANCE_REJECTION")
    if _ma_support_failure(row):
        warnings.append("MA_SUPPORT_FAILURE")
    return [signal for signal in SELL_WARNING_PRIORITY if signal in set(warnings)]


def _resistance_breakout_observation(row: pd.Series) -> bool:
    trigger = _first_price(row, ("breakout_zone_high", "resistance_zone_1_high"))
    return bool(row.get("resistance_zone_breakout_today", False)) and _effective_buy_observation(row, trigger)


def _resistance_turn_support_observation(row: pd.Series) -> bool:
    old_resistance_high = _first_price(row, ("breakout_zone_high",))
    prev_close = _first_price(row, ("prev_close",))
    low = _first_price(row, ("low",))
    close = _first_price(row, ("close",))
    if not all(
        _is_finite_price(value)
        for value in [old_resistance_high, prev_close, low, close]
    ):
        return False
    already_above = prev_close > old_resistance_high
    retest = low <= old_resistance_high * (1.0 + RETEST_TOLERANCE_PCT)
    held = close > old_resistance_high
    first_breakout_same_candle = bool(row.get("resistance_zone_breakout_today", False)) or (
        prev_close <= old_resistance_high and close > old_resistance_high
    )
    supply_pressure = bool(row.get("high_level_supply_pressure", False)) or bool(
        row.get("high_volume_upper_shadow", False)
    )
    return (
        already_above
        and retest
        and held
        and not first_breakout_same_candle
        and not supply_pressure
        and _effective_buy_observation(row, old_resistance_high)
    )


def _failed_breakdown_reclaim_observation(row: pd.Series) -> bool:
    trigger = _first_price(row, ("prev_low", "broken_support_zone_high", "support_zone_1_low"))
    reclaimed = bool(row.get("failed_breakdown", False)) or (
        bool(row.get("break_prev_low", False)) and not bool(row.get("close_below_prev_low", False))
    )
    return reclaimed and _effective_buy_observation(row, trigger)


def _support_rebound_observation(row: pd.Series) -> bool:
    trigger = _first_price(row, ("prev_high", "resistance_zone_1_high"))
    support_turn = bool(row.get("support_zone_holding_today", False)) and bool(
        row.get("close_above_prev_high", False)
    )
    return support_turn and _effective_buy_observation(row, trigger)


def _kd_oversold_recovery_observation(row: pd.Series) -> bool:
    if not bool(row.get("kd_recovery_confirmation", False)):
        return False
    if bool(row.get("high_level_supply_pressure", False)) or bool(
        row.get("high_volume_upper_shadow", False)
    ):
        return False
    return _has_clear_stop_reference(row)


def _effective_buy_observation(row: pd.Series, trigger_price: float | None) -> bool:
    close = _first_price(row, ("close",))
    if not _is_finite_price(close) or not _is_finite_price(trigger_price) or close <= trigger_price:
        return False
    volume = _first_price(row, ("volume",))
    vol_ma5 = _first_price(row, ("vol_ma5",))
    vol_ma20 = _first_price(row, ("vol_ma20",))
    has_volume = (
        _is_finite_price(volume)
        and (
            (_is_finite_price(vol_ma5) and volume > vol_ma5)
            or (_is_finite_price(vol_ma20) and volume > vol_ma20)
        )
    )
    if not has_volume:
        return False
    if float(row.get("close_position_in_range", 0.0) or 0.0) <= 0.6:
        return False
    if bool(row.get("high_level_supply_pressure", False)) or bool(
        row.get("high_volume_upper_shadow", False)
    ):
        return False
    if float(row.get("upper_shadow_pct", 0.0) or 0.0) >= 0.025 and float(
        row.get("close_position_in_range", 0.0) or 0.0
    ) < 0.65:
        return False
    return _has_clear_stop_reference(row)


def _effective_sell_warning_condition(row: pd.Series) -> bool:
    close = _first_price(row, ("close",))
    support_low = _first_price(row, ("support_zone_1_low", "support_1"))
    resistance_high = _first_price(row, ("resistance_zone_1_high", "resistance_1"))
    high = _first_price(row, ("high",))
    return (
        (_is_finite_price(close) and _is_finite_price(support_low) and close < support_low)
        or (
            _is_finite_price(high)
            and _is_finite_price(close)
            and _is_finite_price(resistance_high)
            and high > resistance_high
            and close < resistance_high
        )
        or bool(row.get("close_below_prev_low", False))
        or bool(row.get("price_down_volume_up", False))
    )


def _support_breakdown_warning(row: pd.Series) -> bool:
    close = _first_price(row, ("close",))
    broken_support_low = _first_price(row, ("broken_support_zone_low",))
    support_low = _first_price(row, ("support_zone_1_low", "support_1"))
    prev_low = _first_price(row, ("prev_low",))
    if not _is_finite_price(close):
        return False
    return (
        (_is_finite_price(broken_support_low) and close < broken_support_low)
        or (_is_finite_price(support_low) and close < support_low)
        or bool(row.get("close_below_prev_low", False))
        or (_is_finite_price(prev_low) and close < prev_low)
    )


def _ma_support_failure(row: pd.Series) -> bool:
    if any(bool(row.get(f"ma_break_{window}", False)) for window in (5, 10, 20)):
        return True
    close = _first_price(row, ("close",))
    if not _is_finite_price(close):
        return False
    below_short_ma = any(
        _is_finite_price(ma_value := _first_price(row, (f"ma{window}",))) and close < ma_value
        for window in (5, 10, 20)
    )
    return below_short_ma and row.get("ma_state") in {"MA_BREAK", "BEAR_ALIGNMENT"}


def _has_clear_stop_reference(row: pd.Series) -> bool:
    if _is_finite_price(row.get("invalid_price")):
        return True
    if _first_price(row, ("support_zone_1_low", "support_1", "prev_low")) is not None:
        return True
    stop_reference = row.get("stop_reference")
    return isinstance(stop_reference, str) and bool(stop_reference.strip())


def _split_types(value: object) -> list[str]:
    if value is None or value is pd.NA:
        return []
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return []
    return [item for item in text.split("|") if item]


def _primary_type(value: object, priority: tuple[str, ...]) -> str:
    detail_types = set(_split_types(value))
    for signal_type in priority:
        if signal_type in detail_types:
            return signal_type
    return ""


def _target_resistance(row: pd.Series, columns: tuple[str, ...]) -> float | None:
    close = _first_price(row, ("close",))
    if not _is_finite_price(close):
        return None
    for column in columns:
        value = _first_price(row, (column,))
        if _is_finite_price(value) and value > close:
            return float(value)
    return None


def _first_price(row: pd.Series, columns: tuple[str, ...]) -> float | None:
    for column in columns:
        value = row.get(column)
        if _is_finite_price(value):
            return float(value)
    return None


def _is_finite_price(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(number))


def _signal_stage(row: pd.Series) -> str:
    hard_failed = bool(row.get("support_broken_today", False)) or bool(row.get("margin_crowding_risk", False))
    hard_failed = hard_failed or row.get("trend_state") == "BREAKDOWN"
    hard_failed = hard_failed or bool(row.get("high_level_supply_pressure", False))
    if hard_failed:
        return "FAILED"
    if bool(row.get("kd_recovery_confirmation", False)):
        return "CONFIRMED"
    if row.get("trigger_type") and bool(row.get("volume_expansion", False)) and bool(row.get("close_above_ma5", False)):
        return "CONFIRMED"
    if row.get("trigger_type"):
        return "TRIGGER"
    if row.get("trend_state") in {"UPTREND", "PULLBACK_IN_UPTREND", "RANGE_BOUND"}:
        return "SETUP"
    return "FAILED"


def _invalid_price(row: pd.Series) -> float | None:
    return _first_price(row, ("support_zone_1_low", "support_1", "ma20", "prev_low"))


def _confirm_price(row: pd.Series) -> float | None:
    return _first_price(row, ("resistance_zone_1_high", "resistance_1", "prev_high", "ma5"))


def _non_holder_observation(row: pd.Series) -> str:
    confirm = row.get("confirm_price")
    zone = row.get("resistance_zone_1_label", "")
    if _is_finite_price(confirm):
        if zone:
            return f"觀察壓力區 {zone}，未收盤站上前不追價"
        return f"觀察價/確認價 {float(confirm):.2f}，未站上前不追價"
    return "沒有明確確認價，空手等待下一根訊號"


def _holder_discipline(row: pd.Series) -> str:
    invalid = row.get("invalid_price")
    zone = row.get("support_zone_1_label", "")
    if _is_finite_price(invalid):
        if zone:
            return f"防守支撐區 {zone}，跌破收不回就視為訊號失敗"
        return f"防守價 {float(invalid):.2f}，跌破收不回就視為訊號失敗"
    return "缺少明確防守價，僅列風險暴露觀察"


def _zone_label(row: pd.Series, prefix: str) -> str:
    label = row.get(f"{prefix}_label")
    if label:
        return str(label)
    low = row.get(f"{prefix}_low")
    high = row.get(f"{prefix}_high")
    if pd.isna(low) or pd.isna(high):
        return ""
    low_float = float(low)
    high_float = float(high)
    if abs(low_float - high_float) <= 1e-8:
        return f"{low_float:.2f}"
    return f"{low_float:.2f}~{high_float:.2f}"


def _apply_market_grade_cap(row: pd.Series) -> str:
    grade = str(row.get("grade", ""))
    if not grade:
        return ""
    if row.get("signal_stage") == "FAILED":
        return ""
    if row.get("reversal_state") == "weak_rebound" and grade in {"A", "B"}:
        grade = "C"
    if row.get("market_state") == "MARKET_WEAK_REBOUND" and grade == "A":
        return "B"
    if row.get("market_state") == "MARKET_DOWNTREND" and grade in {"A", "B"}:
        return "C"
    if row.get("market_state") == "MARKET_HIGH_RISK_BREAKDOWN":
        return ""
    return grade


def _hit_rate(frame: pd.DataFrame, side: str, column: str) -> float | None:
    subset = frame[frame["candidate_side"] == side]
    if subset.empty or column not in subset.columns:
        return None
    values = pd.to_numeric(subset[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _mean(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _precision_at(frame: pd.DataFrame, n: int) -> float | None:
    if frame.empty:
        return None
    subset = frame.head(n)
    hits = []
    for _, row in subset.iterrows():
        hit = row.get("hit_d5")
        if pd.isna(hit):
            continue
        hits.append(bool(hit))
    return float(np.mean(hits)) if hits else None
