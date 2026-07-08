"""Margin and short-selling features for the walkline scanner."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_margin_features(
    margin_history: pd.DataFrame,
    walkline_features: pd.DataFrame,
    *,
    asof_date: str,
) -> pd.DataFrame:
    """Compute as-of margin features, using neutral scores when data are absent."""
    if margin_history.empty:
        return _neutral_margin(walkline_features["stock_id"])

    data = margin_history.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="raise")
    data = data[data["trade_date"] <= pd.to_datetime(asof_date)].copy()
    if data.empty:
        return _neutral_margin(walkline_features["stock_id"])

    data["stock_id"] = data["stock_id"].astype(str)
    data["margin_balance"] = pd.to_numeric(data["margin_balance"], errors="coerce").fillna(0.0)
    grouped = data.sort_values(["stock_id", "trade_date"]).groupby("stock_id", sort=False)
    for days in (1, 3, 5, 10):
        data[f"margin_change_{days}d"] = grouped["margin_balance"].diff(days)
        data[f"short_change_{days}d"] = 0.0

    data["margin_consecutive_increase_days"] = grouped["margin_balance"].transform(
        lambda values: _consecutive_diff_tail(values, positive=True)
    )
    data["margin_consecutive_decrease_days"] = grouped["margin_balance"].transform(
        lambda values: _consecutive_diff_tail(values, positive=False)
    )
    latest = data.groupby("stock_id", sort=False).tail(1).copy().reset_index(drop=True)
    latest["short_balance"] = 0.0
    latest["margin_usage_ratio"] = np.nan
    latest["short_margin_ratio"] = np.nan
    latest["short_consecutive_increase_days"] = 0
    latest["short_consecutive_decrease_days"] = 0
    latest["short_covering_pressure"] = 0.0

    context = walkline_features[["stock_id", "return_1d", "support_broken_today", "close_above_prev_high"]]
    latest = latest.merge(context, on="stock_id", how="left")
    latest["price_up_margin_up"] = (latest["return_1d"] > 0) & (latest["margin_change_1d"] > 0)
    latest["price_down_margin_up"] = (latest["return_1d"] < 0) & (latest["margin_change_1d"] > 0)
    latest["price_up_margin_down"] = (latest["return_1d"] > 0) & (latest["margin_change_1d"] < 0)
    latest["price_breakout_short_up"] = False
    latest["margin_score"] = (
        latest["price_up_margin_down"].astype(float) * 3.0
        + (latest["margin_consecutive_decrease_days"] >= 3).astype(float) * 2.0
    ).clip(0, 5)
    latest["short_squeeze_score"] = 0.0
    latest["retail_crowding_risk"] = (
        latest["price_up_margin_up"].astype(float) * 3.0
        + latest["price_down_margin_up"].astype(float) * 4.0
    ).clip(0, 10)
    latest["margin_risk_score"] = (
        latest["retail_crowding_risk"]
        + latest["support_broken_today"].fillna(False).astype(float) * 4.0
    ).clip(0, 10)
    return latest[
        [
            "stock_id",
            "margin_balance",
            "margin_change_1d",
            "margin_change_3d",
            "margin_change_5d",
            "margin_change_10d",
            "margin_usage_ratio",
            "short_balance",
            "short_change_1d",
            "short_change_3d",
            "short_change_5d",
            "short_change_10d",
            "short_margin_ratio",
            "margin_consecutive_increase_days",
            "margin_consecutive_decrease_days",
            "short_consecutive_increase_days",
            "short_consecutive_decrease_days",
            "short_covering_pressure",
            "price_up_margin_up",
            "price_down_margin_up",
            "price_up_margin_down",
            "price_breakout_short_up",
            "margin_score",
            "short_squeeze_score",
            "retail_crowding_risk",
            "margin_risk_score",
        ]
    ]


def _neutral_margin(stock_ids: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"stock_id": stock_ids.astype(str).unique()})
    frame["margin_balance"] = np.nan
    for days in (1, 3, 5, 10):
        frame[f"margin_change_{days}d"] = np.nan
        frame[f"short_change_{days}d"] = np.nan
    frame["margin_usage_ratio"] = np.nan
    frame["short_balance"] = np.nan
    frame["short_margin_ratio"] = np.nan
    frame["margin_consecutive_increase_days"] = 0
    frame["margin_consecutive_decrease_days"] = 0
    frame["short_consecutive_increase_days"] = 0
    frame["short_consecutive_decrease_days"] = 0
    frame["short_covering_pressure"] = 0.0
    frame["price_up_margin_up"] = False
    frame["price_down_margin_up"] = False
    frame["price_up_margin_down"] = False
    frame["price_breakout_short_up"] = False
    frame["margin_score"] = 0.0
    frame["short_squeeze_score"] = 0.0
    frame["retail_crowding_risk"] = 0.0
    frame["margin_risk_score"] = 0.0
    return frame


def _consecutive_diff_tail(values: pd.Series, *, positive: bool) -> pd.Series:
    diff = values.diff()
    counts: list[int] = []
    current = 0
    for value in diff:
        ok = value > 0 if positive else value < 0
        current = current + 1 if ok else 0
        counts.append(current)
    return pd.Series(counts, index=values.index)
