"""Institutional and large-holder chip features."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_chip_features(chip_history: pd.DataFrame, *, asof_date: str) -> pd.DataFrame:
    """Compute as-of institutional flow aggregates."""
    if chip_history.empty:
        return pd.DataFrame(
            columns=[
                "stock_id",
                "foreign_5d",
                "investment_trust_5d",
                "dealer_5d",
                "institutional_score",
                "institutional_selling_score",
            ]
        )
    data = chip_history.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="raise")
    data = data[data["trade_date"] <= pd.to_datetime(asof_date)].copy()
    if data.empty:
        return pd.DataFrame()
    data["stock_id"] = data["stock_id"].astype(str)
    numeric_columns = [
        "foreign_net_buy_shares",
        "trust_net_buy_shares",
        "dealer_net_buy_shares",
        "dealer_hedge_net_buy_shares",
        "institutional_net_buy_shares",
    ]
    for column in numeric_columns:
        if column not in data.columns:
            data[column] = 0.0
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)

    grouped = data.sort_values(["stock_id", "trade_date"]).groupby("stock_id", sort=False)
    for days in (3, 5, 10, 20):
        data[f"foreign_{days}d"] = grouped["foreign_net_buy_shares"].transform(
            lambda series, window=days: series.rolling(window, min_periods=1).sum()
        )
        data[f"investment_trust_{days}d"] = grouped["trust_net_buy_shares"].transform(
            lambda series, window=days: series.rolling(window, min_periods=1).sum()
        )
        data[f"dealer_{days}d"] = grouped["dealer_net_buy_shares"].transform(
            lambda series, window=days: series.rolling(window, min_periods=1).sum()
        )

    data["foreign_consecutive_buy_days"] = grouped["foreign_net_buy_shares"].transform(
        _consecutive_positive_tail
    )
    data["foreign_consecutive_sell_days"] = grouped["foreign_net_buy_shares"].transform(
        _consecutive_negative_tail
    )
    data["investment_trust_consecutive_buy_days"] = grouped["trust_net_buy_shares"].transform(
        _consecutive_positive_tail
    )
    data["investment_trust_consecutive_sell_days"] = grouped["trust_net_buy_shares"].transform(
        _consecutive_negative_tail
    )

    latest = data.groupby("stock_id", sort=False).tail(1).copy().reset_index(drop=True)
    latest["foreign_buy_sell"] = latest["foreign_net_buy_shares"]
    latest["investment_trust_buy_sell"] = latest["trust_net_buy_shares"]
    latest["dealer_buy_sell"] = latest["dealer_net_buy_shares"]
    latest["dealer_hedge_buy_sell"] = latest["dealer_hedge_net_buy_shares"]
    latest["institutional_total_buy_sell"] = latest["institutional_net_buy_shares"]
    latest["foreign_score"] = _flow_score(latest["foreign_5d"], positive_cap=4)
    latest["investment_trust_score"] = _flow_score(latest["investment_trust_5d"], positive_cap=4)
    latest["dealer_score"] = _flow_score(latest["dealer_5d"], positive_cap=2)
    latest["institutional_score"] = (
        latest["foreign_score"] + latest["investment_trust_score"] + latest["dealer_score"]
    ).clip(0, 10)
    latest["institutional_selling_score"] = (
        _flow_score(-latest["foreign_5d"], positive_cap=4)
        + _flow_score(-latest["investment_trust_5d"], positive_cap=4)
        + _flow_score(-latest["dealer_5d"], positive_cap=2)
    ).clip(0, 10)
    latest["institutional_buy_ratio_to_volume"] = np.nan
    latest["institutional_sell_ratio_to_volume"] = np.nan
    return latest


def compute_big_holder_features(
    holder_latest: pd.DataFrame,
    walkline_features: pd.DataFrame,
) -> pd.DataFrame:
    """Compute TDCC large-holder features, falling back to main-force proxy."""
    if holder_latest.empty:
        return _main_force_proxy(walkline_features)
    holder = holder_latest.copy()
    holder["stock_id"] = holder["stock_id"].astype(str)
    score_source = pd.to_numeric(
        holder.get("big_holder_ratio_1000_lots_pct", pd.Series(0.0, index=holder.index)),
        errors="coerce",
    )
    score_ma = pd.to_numeric(
        holder.get("big_holder_ratio_1000_lots_pct_ma20", pd.Series(np.nan, index=holder.index)),
        errors="coerce",
    )
    holder["holder_1000_lots_ratio"] = score_source
    holder["holder_400_lots_ratio"] = np.nan
    holder["large_holder_ratio"] = score_source
    holder["large_holder_weekly_change"] = score_source - score_ma
    holder["retail_holder_ratio"] = np.nan
    holder["retail_holder_weekly_change"] = np.nan
    holder["concentration_score"] = np.where(holder["large_holder_weekly_change"] > 0, 2.5, 0.0)
    holder["big_holder_score"] = holder["concentration_score"].clip(0, 5)
    holder["big_holder_data_source"] = "tdcc"
    return holder[
        [
            "stock_id",
            "holder_400_lots_ratio",
            "holder_1000_lots_ratio",
            "large_holder_ratio",
            "large_holder_weekly_change",
            "retail_holder_ratio",
            "retail_holder_weekly_change",
            "concentration_score",
            "big_holder_score",
            "big_holder_data_source",
        ]
    ]


def _main_force_proxy(walkline_features: pd.DataFrame) -> pd.DataFrame:
    data = walkline_features.copy()
    data["high_volume_red_k"] = data["long_red_k"] & data["volume_expansion"]
    data["high_volume_black_k"] = data["long_black_k"] & data["volume_expansion"]
    data["support_hold_after_pullback"] = data["low_volume_pullback"] & (
        data["close"] >= data["support_1"].fillna(data["close"])
    )
    data["failed_breakout_supply"] = data["failed_breakout"] | data["high_volume_upper_shadow"]
    data["institution_buy_price_weak"] = False
    data["institution_sell_price_strong"] = False
    data["main_force_proxy_score"] = (
        data["low_volume_pullback"].astype(float) * 1.5
        + data["support_hold_after_pullback"].astype(float) * 1.5
        + data["high_volume_red_k"].astype(float) * 1.0
    ).clip(0, 5)
    data["supply_pressure_score"] = (
        data["high_volume_black_k"].astype(float) * 2.0
        + data["failed_breakout_supply"].astype(float) * 2.0
        + data["high_volume_upper_shadow"].astype(float) * 1.0
    ).clip(0, 5)
    data["big_holder_score"] = (data["main_force_proxy_score"] - data["supply_pressure_score"] / 2).clip(0, 5)
    data["big_holder_data_source"] = "main_force_proxy"
    columns = [
        "stock_id",
        "high_volume_red_k",
        "high_volume_black_k",
        "low_volume_pullback",
        "support_hold_after_pullback",
        "failed_breakout_supply",
        "high_volume_upper_shadow",
        "institution_buy_price_weak",
        "institution_sell_price_strong",
        "main_force_proxy_score",
        "supply_pressure_score",
        "big_holder_score",
        "big_holder_data_source",
    ]
    return data[columns]


def _flow_score(values: pd.Series, *, positive_cap: float) -> pd.Series:
    scaled = np.log1p(values.clip(lower=0.0).abs()) / 4.0
    return pd.Series(scaled, index=values.index).clip(0, positive_cap)


def _consecutive_positive_tail(values: pd.Series) -> pd.Series:
    return _consecutive_tail(values, positive=True)


def _consecutive_negative_tail(values: pd.Series) -> pd.Series:
    return _consecutive_tail(values, positive=False)


def _consecutive_tail(values: pd.Series, *, positive: bool) -> pd.Series:
    counts: list[int] = []
    current = 0
    for value in values:
        ok = value > 0 if positive else value < 0
        current = current + 1 if ok else 0
        counts.append(current)
    return pd.Series(counts, index=values.index)
