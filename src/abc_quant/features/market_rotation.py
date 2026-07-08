"""Market, sector, and concept rotation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def load_concept_stock_map(path: str | Path) -> dict[str, list[str]]:
    """Load the manually maintained concept-stock map."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"concept stock map must be a mapping: {config_path}")
    return {str(key): [str(value) for value in values or []] for key, values in data.items()}


def classify_market_state(
    market_history: pd.DataFrame,
    price_history: pd.DataFrame,
    *,
    asof_date: str,
) -> dict[str, Any]:
    """Classify the broad market, falling back to an equal-weight proxy."""
    market = _prepare_market_history(market_history, price_history, asof_date=asof_date)
    if market.empty:
        return {
            "market_state": "MARKET_RANGE_BOUND",
            "market_score": 3,
            "market_risk_score": 3,
            "support_levels": [],
            "resistance_levels": [],
            "source": "unavailable",
        }

    latest = market.tail(1).iloc[0]
    close = float(latest["close"])
    ma5 = float(latest["ma5"])
    ma10 = float(latest["ma10"])
    ma20 = float(latest["ma20"])
    ma60 = float(latest["ma60"])
    ma5_slope = float(latest.get("ma5_slope", 0.0))
    ma10_slope = float(latest.get("ma10_slope", 0.0))
    ma20_slope = float(latest.get("ma20_slope", 0.0))
    long_black = bool(latest.get("long_black_k", False))
    volume_expansion = bool(latest.get("volume_expansion", False))
    state = "MARKET_RANGE_BOUND"
    if close > ma5 > ma10 > ma20 > ma60 and ma5_slope > 0 and ma10_slope > 0 and ma20_slope > 0:
        state = "MARKET_STRONG_UPTREND"
    elif (close < ma5 or close < ma10) and close > ma60:
        state = "MARKET_PULLBACK_IN_UPTREND"
    elif close < ma60 and (long_black or volume_expansion or close < latest.get("low_60d", close)):
        state = "MARKET_HIGH_RISK_BREAKDOWN"
    elif close < ma20 and ma5 < ma10 < ma20:
        state = "MARKET_DOWNTREND"
    elif close < ma5 and close < ma10 and latest.get("return_1d", 0.0) > 0:
        state = "MARKET_WEAK_REBOUND"

    score_map = {
        "MARKET_STRONG_UPTREND": (10, 1),
        "MARKET_PULLBACK_IN_UPTREND": (6, 4),
        "MARKET_RANGE_BOUND": (4, 4),
        "MARKET_WEAK_REBOUND": (2, 7),
        "MARKET_DOWNTREND": (1, 8),
        "MARKET_HIGH_RISK_BREAKDOWN": (0, 10),
    }
    market_score, market_risk_score = score_map[state]
    supports = _levels([latest.get("low_20d"), latest.get("low_60d"), ma20, ma60], close, below=True)
    resistances = _levels([latest.get("high_20d"), latest.get("high_60d"), ma5, ma10], close, below=False)
    return {
        "market_state": state,
        "market_score": market_score,
        "market_risk_score": market_risk_score,
        "support_levels": supports,
        "resistance_levels": resistances,
        "source": str(latest.get("source", "market_proxy")),
    }


def compute_sector_rotation(
    walkline_features: pd.DataFrame,
    stock_info: pd.DataFrame,
    sector_sentiment: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return per-sector rotation rows and stock-to-sector context."""
    stock_context = walkline_features[["stock_id", "return_5d", "return_10d", "return_20d", "close_above_ma20"]].copy()
    info = stock_info[["stock_id", "stock_name", "sector"]].copy() if not stock_info.empty else pd.DataFrame()
    if not info.empty:
        stock_context = stock_context.merge(info, on="stock_id", how="left")
    stock_context["sector"] = stock_context["sector"].fillna("UNKNOWN")
    grouped = stock_context.groupby("sector", dropna=False)
    rotation = grouped.agg(
        sector_return_5d=("return_5d", "mean"),
        sector_return_10d=("return_10d", "mean"),
        sector_return_20d=("return_20d", "mean"),
        sector_above_ma20_ratio=("close_above_ma20", "mean"),
        member_count=("stock_id", "count"),
    ).reset_index()
    rotation["sector_return_1d"] = np.nan
    rotation["sector_return_3d"] = np.nan
    rotation["sector_volume_ratio_5"] = np.nan
    rotation["sector_volume_ratio_20"] = np.nan
    rotation["sector_relative_strength_vs_market_5d"] = rotation["sector_return_5d"] - rotation["sector_return_5d"].mean()
    rotation["sector_relative_strength_vs_market_10d"] = rotation["sector_return_10d"] - rotation["sector_return_10d"].mean()
    rotation["sector_relative_strength_vs_market_20d"] = rotation["sector_return_20d"] - rotation["sector_return_20d"].mean()
    rotation["sector_below_ma20_ratio"] = 1.0 - rotation["sector_above_ma20_ratio"]
    rotation["sector_new_20d_high_ratio"] = np.nan
    rotation["sector_new_20d_low_ratio"] = np.nan
    rotation["sector_leader_strength"] = rotation["sector_return_20d"].rank(pct=True).fillna(0.5) * 100
    rotation["sector_laggard_rebound_score"] = np.where(rotation["sector_return_5d"] > 0, 50, 0)
    rotation["sector_distribution_risk"] = rotation["sector_below_ma20_ratio"].fillna(0.5) * 100
    rotation["sector_strength_score"] = (
        rotation["sector_return_20d"].rank(pct=True).fillna(0.5) * 50
        + rotation["sector_above_ma20_ratio"].fillna(0.5) * 50
    ).clip(0, 100)
    rotation["sector_risk_score"] = (
        rotation["sector_below_ma20_ratio"].fillna(0.5) * 60
        + (rotation["sector_return_5d"].fillna(0) < 0).astype(float) * 40
    ).clip(0, 100)
    rotation = rotation.sort_values("sector_strength_score", ascending=False).reset_index(drop=True)
    rotation["sector_rotation_rank"] = np.arange(1, len(rotation) + 1)
    rotation["sector_state"] = np.select(
        [
            rotation["sector_strength_score"] >= 75,
            rotation["sector_strength_score"] >= 60,
            (rotation["sector_strength_score"] >= 45) & (rotation["sector_risk_score"] < 55),
            rotation["sector_risk_score"] >= 75,
            rotation["sector_risk_score"] >= 60,
        ],
        [
            "SECTOR_LEADING",
            "SECTOR_ROTATING_IN",
            "SECTOR_PULLBACK_HEALTHY",
            "SECTOR_WEAK",
            "SECTOR_ROTATING_OUT",
        ],
        default="SECTOR_RANGE_BOUND",
    )
    rotation["sector_reason"] = rotation.apply(
        lambda row: f"20日均線上方比率 {row['sector_above_ma20_ratio']:.0%}，20日報酬 {row['sector_return_20d']:.2%}",
        axis=1,
    )
    stock_context = stock_context.merge(
        rotation[["sector", "sector_rotation_rank", "sector_strength_score", "sector_risk_score", "sector_state"]],
        on="sector",
        how="left",
    )
    return rotation, stock_context


def compute_concept_rotation(
    walkline_features: pd.DataFrame,
    concept_map: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return concept rotation rows and stock-to-concept context from config."""
    rows: list[dict[str, Any]] = []
    stock_rows: list[dict[str, Any]] = []
    for concept, members in concept_map.items():
        member_set = {str(member) for member in members}
        frame = walkline_features[walkline_features["stock_id"].isin(member_set)].copy()
        if frame.empty:
            rows.append(_empty_concept_row(concept))
            continue
        leader = frame.sort_values("return_20d", ascending=False).iloc[0]
        row = {
            "concept": concept,
            "concept_return_1d": frame["return_1d"].mean(),
            "concept_return_3d": frame["return_3d"].mean(),
            "concept_return_5d": frame["return_5d"].mean(),
            "concept_return_10d": frame["return_10d"].mean(),
            "concept_return_20d": frame["return_20d"].mean(),
            "concept_volume_expansion_ratio": frame["volume_expansion"].mean(),
            "concept_above_ma20_ratio": frame["close_above_ma20"].mean(),
            "concept_below_ma20_ratio": 1.0 - frame["close_above_ma20"].mean(),
            "concept_new_20d_high_ratio": (frame["distance_to_20d_high"] <= 0.01).mean(),
            "concept_leader_stock": leader["stock_id"],
            "concept_leader_breakdown": bool(leader["support_broken_today"]),
            "concept_laggard_rebound": bool((frame["return_5d"] > 0).any()),
        }
        rows.append(row)
        for stock_id in member_set:
            stock_rows.append({"stock_id": stock_id, "concept": concept})

    rotation = pd.DataFrame(rows)
    if rotation.empty:
        return rotation, pd.DataFrame(columns=["stock_id", "concepts"])
    rotation["concept_strength_score"] = (
        rotation["concept_return_20d"].rank(pct=True).fillna(0.5) * 50
        + rotation["concept_above_ma20_ratio"].fillna(0.0) * 50
    ).clip(0, 100)
    rotation["concept_risk_score"] = (
        rotation["concept_below_ma20_ratio"].fillna(1.0) * 60
        + rotation["concept_leader_breakdown"].fillna(False).astype(float) * 40
    ).clip(0, 100)
    rotation = rotation.sort_values("concept_strength_score", ascending=False).reset_index(drop=True)
    rotation["concept_rotation_rank"] = np.arange(1, len(rotation) + 1)
    stock_context = (
        pd.DataFrame(stock_rows)
        .groupby("stock_id")["concept"]
        .agg(lambda values: sorted(set(values)))
        .reset_index(name="concepts")
    )
    score_map = rotation.set_index("concept")[
        ["concept_rotation_rank", "concept_strength_score", "concept_risk_score"]
    ].to_dict(orient="index")
    stock_context["concept_rotation_rank"] = stock_context["concepts"].map(
        lambda concepts: min(score_map[c]["concept_rotation_rank"] for c in concepts if c in score_map)
    )
    stock_context["concept_strength_score"] = stock_context["concepts"].map(
        lambda concepts: max(score_map[c]["concept_strength_score"] for c in concepts if c in score_map)
    )
    stock_context["concept_risk_score"] = stock_context["concepts"].map(
        lambda concepts: max(score_map[c]["concept_risk_score"] for c in concepts if c in score_map)
    )
    return rotation, stock_context


def _prepare_market_history(
    market_history: pd.DataFrame,
    price_history: pd.DataFrame,
    *,
    asof_date: str,
) -> pd.DataFrame:
    cutoff = pd.to_datetime(asof_date)
    if not market_history.empty:
        data = market_history.copy()
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data[data["date"] <= cutoff].copy()
        if not data.empty and data["date"].max().date().isoformat() == asof_date:
            data = data.sort_values("date")
            data["source"] = "official_index"
            return _add_market_rolling(data)

    price = price_history.copy()
    price["date"] = pd.to_datetime(price["date"], errors="raise")
    price = price[price["date"] <= cutoff].copy()
    if price.empty:
        return pd.DataFrame()
    proxy = price.groupby("date").agg(
        open=("open", "mean"),
        high=("high", "mean"),
        low=("low", "mean"),
        close=("close", "mean"),
        volume=("volume", "sum"),
    ).reset_index()
    proxy["index_id"] = "MARKET_PROXY"
    proxy["index_name"] = "equal_weight_stock_proxy"
    proxy["source"] = "equal_weight_stock_proxy"
    return _add_market_rolling(proxy)


def _add_market_rolling(data: pd.DataFrame) -> pd.DataFrame:
    data = data.sort_values("date").copy()
    for window in (5, 10, 20, 60, 120, 240):
        if f"ma{window}" not in data.columns:
            data[f"ma{window}"] = data["close"].rolling(window, min_periods=1).mean()
        data[f"ma{window}_slope"] = data[f"ma{window}"].diff(3)
    data["return_1d"] = data["close"].pct_change()
    data["return_3d"] = data["close"].pct_change(3)
    data["return_5d"] = data["close"].pct_change(5)
    data["return_10d"] = data["close"].pct_change(10)
    data["high_20d"] = data["high"].rolling(20, min_periods=1).max()
    data["low_20d"] = data["low"].rolling(20, min_periods=1).min()
    data["high_60d"] = data["high"].rolling(60, min_periods=1).max()
    data["low_60d"] = data["low"].rolling(60, min_periods=1).min()
    data["drawdown_from_20d_high"] = data["close"] / data["high_20d"] - 1.0
    data["drawdown_from_60d_high"] = data["close"] / data["high_60d"] - 1.0
    data["long_black_k"] = ((data["close"] - data["open"]) / data["close"]) <= -0.025
    data["vol_ma20"] = data["volume"].rolling(20, min_periods=1).mean()
    data["volume_expansion"] = data["volume"] > data["vol_ma20"] * 1.3
    return data


def _levels(values: list[Any], close: float, *, below: bool) -> list[float]:
    result: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(number):
            continue
        if (below and number <= close) or (not below and number >= close):
            result.append(round(number, 4))
    return sorted(set(result), reverse=below)[:3]


def _empty_concept_row(concept: str) -> dict[str, Any]:
    return {
        "concept": concept,
        "concept_return_1d": np.nan,
        "concept_return_3d": np.nan,
        "concept_return_5d": np.nan,
        "concept_return_10d": np.nan,
        "concept_return_20d": np.nan,
        "concept_volume_expansion_ratio": np.nan,
        "concept_above_ma20_ratio": np.nan,
        "concept_below_ma20_ratio": np.nan,
        "concept_new_20d_high_ratio": np.nan,
        "concept_leader_stock": "",
        "concept_leader_breakdown": False,
        "concept_laggard_rebound": False,
    }
