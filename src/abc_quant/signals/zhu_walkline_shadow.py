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


@dataclass(frozen=True)
class ZhuWalklineResult:
    asof_date: str
    mode: str
    formal_champion_changed: bool
    formal_trade_effect: bool
    web_research_used: bool
    web_research_is_supplementary: bool
    feature_matrix: pd.DataFrame
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
    holder = compute_big_holder_features(bundle.holder_latest, walkline)
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
    top_rise = features[features["grade"] != ""].sort_values(
        ["rise_score", "fall_risk_score"], ascending=[False, True]
    ).head(top_n)
    top_fall = features[features["risk_grade"] != ""].sort_values(
        ["fall_risk_score", "rise_score"], ascending=[False, True]
    ).head(top_n)
    run_notes = list(bundle.data_quality.warnings)
    if not web_research_used:
        run_notes.append("未啟用或無法使用網路搜尋，本次分析僅使用本地資料庫。")
    return ZhuWalklineResult(
        asof_date=bundle.asof_date,
        mode="shadow_advisory_only",
        formal_champion_changed=False,
        formal_trade_effect=False,
        web_research_used=web_research_used,
        web_research_is_supplementary=True,
        feature_matrix=features,
        top_rise_candidates=top_rise,
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
            if len(stock_future) >= horizon:
                value = float(stock_future.loc[horizon - 1, "close"] / stock["close"] - 1.0)
            row[f"future_return_d{horizon}"] = value
            row[f"hit_d{horizon}"] = bool(value > 0) if stock["candidate_side"] == "rise" else bool(value < 0)
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
        lambda row: [row["support_1"]] if bool(row["support_broken_today"]) and pd.notna(row["support_1"]) else [],
        axis=1,
    )
    features["next_support"] = features.apply(
        lambda row: [value for value in [row.get("support_1"), row.get("support_2")] if pd.notna(value)],
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
    if not reasons:
        reasons.append("未達明顯風險條件")
    return reasons


def _hit_rate(frame: pd.DataFrame, side: str, column: str) -> float | None:
    subset = frame[frame["candidate_side"] == side]
    if subset.empty:
        return None
    return float(subset[column].mean())


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
        hits.append(bool(row["hit_d5"]))
    return float(np.mean(hits)) if hits else None
