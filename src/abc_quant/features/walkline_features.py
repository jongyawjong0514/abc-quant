"""Walkline-style technical features for Taiwan stock shadow scans."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


MOVING_AVERAGE_WINDOWS = (5, 10, 20, 60, 120, 240)
RETURN_WINDOWS = (1, 3, 5, 10, 20)
ZONE_MERGE_PCT = 0.015
MAX_PRICE_ZONES = 3
KD_LOOKBACK = 9
KD_SMOOTHING = 3
KD_OVERSOLD_LEVEL = 20.0
KD_RECENT_OVERSOLD_WINDOW = 5
KD_TIGHT_BODY_MAX_PCT = 0.012
KD_PRIOR_TIGHT_LOW_VOLUME_WINDOW = 5


def compute_walkline_features(price_history: pd.DataFrame, *, asof_date: str) -> pd.DataFrame:
    """Compute latest as-of walkline features for each stock.

    All rolling and shifted features are calculated after filtering rows to
    ``date <= asof_date``. The returned frame contains one latest row per stock.
    """
    data = compute_walkline_feature_history(price_history, asof_date=asof_date)
    latest = data.groupby("stock_id", group_keys=False, sort=False).tail(1).copy().reset_index(drop=True)
    latest["asof_date"] = asof_date
    _add_support_resistance(latest)
    _add_kd_observation_features(latest)
    return latest


def compute_walkline_feature_history(
    price_history: pd.DataFrame,
    *,
    asof_date: str,
) -> pd.DataFrame:
    """Compute causal walkline features for every row through ``asof_date``."""
    data = _prepare_price_history(price_history, asof_date=asof_date)
    grouped = data.groupby("stock_id", group_keys=False, sort=False)

    data["turnover"] = data["close"] * data["volume"]
    for window in RETURN_WINDOWS:
        data[f"return_{window}d"] = grouped["close"].pct_change(window)
    for window in (20, 60):
        data[f"high_{window}d"] = grouped["high"].transform(
            lambda series, rolling_window=window: series.rolling(
                rolling_window, min_periods=1
            ).max()
        )
        data[f"low_{window}d"] = grouped["low"].transform(
            lambda series, rolling_window=window: series.rolling(
                rolling_window, min_periods=1
            ).min()
        )
        data[f"drawdown_from_{window}d_high"] = _safe_div(
            data["close"] - data[f"high_{window}d"], data[f"high_{window}d"]
        )
        data[f"distance_to_{window}d_high"] = _safe_div(
            data[f"high_{window}d"] - data["close"], data["close"]
        )

    for window in MOVING_AVERAGE_WINDOWS:
        data[f"ma{window}"] = grouped["close"].transform(
            lambda series, rolling_window=window: series.rolling(
                rolling_window, min_periods=1
            ).mean()
        )
        data[f"ma{window}_slope"] = grouped[f"ma{window}"].diff(3)
        data[f"close_above_ma{window}"] = data["close"] > data[f"ma{window}"]

    data["vol_ma5"] = grouped["volume"].transform(lambda s: s.rolling(5, min_periods=1).mean())
    data["vol_ma20"] = grouped["volume"].transform(
        lambda s: s.rolling(20, min_periods=1).mean()
    )
    data["vol_ratio_5"] = _safe_div(data["volume"], data["vol_ma5"])
    data["vol_ratio_20"] = _safe_div(data["volume"], data["vol_ma20"])
    data["amount_ma5"] = grouped["turnover"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    data["amount_ma20"] = grouped["turnover"].transform(
        lambda s: s.rolling(20, min_periods=1).mean()
    )
    data["amount_ratio_5"] = _safe_div(data["turnover"], data["amount_ma5"])
    data["amount_ratio_20"] = _safe_div(data["turnover"], data["amount_ma20"])

    data["prev_open"] = grouped["open"].shift(1)
    data["prev_high"] = grouped["high"].shift(1)
    data["prev_low"] = grouped["low"].shift(1)
    data["prev_close"] = grouped["close"].shift(1)
    data["swing_high_3d"] = grouped["high"].transform(
        lambda s: s.rolling(3, min_periods=1).max()
    )
    data["swing_low_3d"] = grouped["low"].transform(lambda s: s.rolling(3, min_periods=1).min())
    data["swing_high_1"] = grouped["high"].transform(lambda s: s.rolling(5, min_periods=1).max())
    data["swing_high_2"] = grouped["high"].transform(
        lambda s: s.rolling(20, min_periods=1).max()
    )
    data["swing_low_1"] = grouped["low"].transform(lambda s: s.rolling(5, min_periods=1).min())
    data["swing_low_2"] = grouped["low"].transform(lambda s: s.rolling(20, min_periods=1).min())
    data["higher_high"] = data["swing_high_1"] > grouped["swing_high_1"].shift(5)
    data["lower_high"] = data["swing_high_1"] < grouped["swing_high_1"].shift(5)
    data["higher_low"] = data["swing_low_1"] > grouped["swing_low_1"].shift(5)
    data["lower_low"] = data["swing_low_1"] < grouped["swing_low_1"].shift(5)
    data["prev_low_20d"] = grouped["low_20d"].shift(1)

    data["ma_bull_alignment"] = (
        (data["close"] > data["ma5"])
        & (data["ma5"] > data["ma10"])
        & (data["ma10"] > data["ma20"])
        & (data["ma20"] > data["ma60"])
    )
    data["ma_bear_alignment"] = (
        (data["close"] < data["ma5"])
        & (data["ma5"] < data["ma10"])
        & (data["ma10"] < data["ma20"])
    )
    ma_stack = data[["ma5", "ma10", "ma20"]]
    data["ma_compression"] = _safe_div(ma_stack.max(axis=1) - ma_stack.min(axis=1), data["close"]) <= 0.03

    for window in (5, 10, 20):
        ma_col = f"ma{window}"
        previous_ma = grouped[ma_col].shift(1)
        data[f"ma_reclaim_{window}"] = (data["close"] > data[ma_col]) & (
            data["prev_close"] <= previous_ma
        )
        data[f"ma_break_{window}"] = (data["close"] < data[ma_col]) & (
            data["prev_close"] >= previous_ma
        )

    _add_kline_features(data)
    data = data.copy()
    _add_volume_state_features(data)
    data = data.copy()
    _add_kd_features(data)
    data = data.copy()
    _add_price_zone_source_features(data)
    data = data.copy()
    _add_state_labels(data)
    return data


def compute_kd_observation_history(
    price_history: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Build daily point-in-time KD observation rows with one feature pass."""
    data = compute_walkline_feature_history(price_history, asof_date=end_date)
    dates = pd.to_datetime(data["date"], errors="coerce")
    start = pd.to_datetime(start_date, errors="raise")
    end = pd.to_datetime(end_date, errors="raise")
    observation_dates = sorted(
        pd.Timestamp(value) for value in dates[dates.between(start, end)].unique()
    )
    if not observation_dates:
        return data.iloc[0:0].copy()

    daily_frames: list[pd.DataFrame] = []
    for asof_date in observation_dates:
        available = data.loc[dates <= asof_date]
        daily = (
            available.groupby("stock_id", group_keys=False, sort=False)
            .tail(1)
            .copy()
            .reset_index(drop=True)
        )
        daily["asof_date"] = asof_date.date().isoformat()
        _add_support_resistance(daily)
        _add_kd_observation_features(daily)
        daily_frames.append(daily)
    return pd.concat(daily_frames, ignore_index=True)


def forbidden_signal_feature_columns(columns: Iterable[str]) -> list[str]:
    """Return columns that must not be present in same-day signal features."""
    forbidden_prefixes = ("future_return", "label_d")
    return [column for column in columns if column.startswith(forbidden_prefixes)]


def _prepare_price_history(price_history: pd.DataFrame, *, asof_date: str) -> pd.DataFrame:
    required = {"date", "stock_id", "open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(price_history.columns))
    if missing:
        raise ValueError("price history missing required columns: " + ", ".join(missing))
    data = price_history.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    cutoff = pd.to_datetime(asof_date)
    data = data[data["date"] <= cutoff].copy()
    if data.empty:
        raise ValueError(f"price history has no rows at or before {asof_date}")
    data["stock_id"] = data["stock_id"].astype(str)
    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close", "volume"])
    return data.sort_values(["stock_id", "date"]).reset_index(drop=True)


def _add_kline_features(data: pd.DataFrame) -> None:
    price_range = (data["high"] - data["low"]).replace(0.0, np.nan)
    body = data["close"] - data["open"]
    data["k_body_pct"] = _safe_div(body.abs(), data["close"])
    data["upper_shadow_pct"] = _safe_div(
        data["high"] - data[["open", "close"]].max(axis=1), data["close"]
    )
    data["lower_shadow_pct"] = _safe_div(
        data[["open", "close"]].min(axis=1) - data["low"], data["close"]
    )
    data["close_position_in_range"] = _safe_div(data["close"] - data["low"], price_range).fillna(0.5)
    data["red_k"] = data["close"] > data["open"]
    data["black_k"] = data["close"] < data["open"]
    data["long_red_k"] = data["red_k"] & (data["k_body_pct"] >= 0.03) & (
        data["close_position_in_range"] >= 0.7
    )
    data["long_black_k"] = data["black_k"] & (data["k_body_pct"] >= 0.03) & (
        data["close_position_in_range"] <= 0.3
    )
    data["gap_up"] = data["open"] > data["prev_high"] * 1.005
    data["gap_down"] = data["open"] < data["prev_low"] * 0.995
    data["break_prev_high"] = data["high"] > data["prev_high"]
    data["break_prev_low"] = data["low"] < data["prev_low"]
    data["close_above_prev_high"] = data["close"] > data["prev_high"]
    data["close_below_prev_low"] = data["close"] < data["prev_low"]
    data["hammer_like"] = (data["lower_shadow_pct"] >= data["k_body_pct"] * 1.5) & (
        data["close_position_in_range"] >= 0.55
    )
    data["shooting_star_like"] = (data["upper_shadow_pct"] >= data["k_body_pct"] * 1.5) & (
        data["close_position_in_range"] <= 0.55
    )
    data["engulfing_bullish_like"] = data["red_k"] & (data["open"] <= data["prev_close"]) & (
        data["close"] >= data["prev_open"]
    )
    data["engulfing_bearish_like"] = data["black_k"] & (data["open"] >= data["prev_close"]) & (
        data["close"] <= data["prev_open"]
    )
    data["inside_bar"] = (data["high"] <= data["prev_high"]) & (data["low"] >= data["prev_low"])
    data["outside_bar"] = (data["high"] >= data["prev_high"]) & (data["low"] <= data["prev_low"])
    data["failed_breakout"] = data["break_prev_high"] & (data["close"] < data["prev_high"])
    data["failed_breakdown"] = data["break_prev_low"] & (data["close"] > data["prev_low"])


def _add_volume_state_features(data: pd.DataFrame) -> None:
    data["volume_expansion"] = data["vol_ratio_20"] >= 1.3
    data["volume_contraction"] = data["vol_ratio_20"] <= 0.75
    data["price_up_volume_up"] = (data["return_1d"] > 0) & data["volume_expansion"]
    data["price_up_volume_down"] = (data["return_1d"] > 0) & data["volume_contraction"]
    data["price_down_volume_up"] = (data["return_1d"] < 0) & data["volume_expansion"]
    data["price_down_volume_down"] = (data["return_1d"] < 0) & data["volume_contraction"]
    data["high_volume_upper_shadow"] = data["volume_expansion"] & (
        data["upper_shadow_pct"] >= 0.025
    )
    data["high_volume_long_black"] = data["volume_expansion"] & data["long_black_k"]
    data["low_volume_pullback"] = (data["return_1d"] < 0) & data["volume_contraction"] & (
        data["close"] >= data["ma20"]
    )


def _add_kd_features(data: pd.DataFrame) -> None:
    """Add point-in-time KD(9, 3, 3) and post-oversold transition fields."""
    grouped = data.groupby("stock_id", group_keys=False, sort=False)
    data["kd_open_close_body_pct"] = _safe_div(
        (data["close"] - data["open"]).abs(), data["open"]
    )
    data["kd_tight_low_volume_day"] = (
        (data["kd_open_close_body_pct"] <= KD_TIGHT_BODY_MAX_PCT)
        & data["volume_contraction"].fillna(False).astype(bool)
    )
    quiet_day_grouped = data.groupby("stock_id", group_keys=False, sort=False)[
        "kd_tight_low_volume_day"
    ]
    data["kd_prior_5d_tight_low_volume_count"] = quiet_day_grouped.transform(
        lambda series: (
            series.shift(1)
            .rolling(KD_PRIOR_TIGHT_LOW_VOLUME_WINDOW, min_periods=KD_PRIOR_TIGHT_LOW_VOLUME_WINDOW)
            .sum()
            .fillna(0)
            .astype(int)
        )
    )
    data["kd_prior_5d_tight_low_volume_gate"] = (
        data["kd_prior_5d_tight_low_volume_count"] >= 1
    )
    rolling_low = grouped["low"].transform(
        lambda series: series.rolling(KD_LOOKBACK, min_periods=1).min()
    )
    rolling_high = grouped["high"].transform(
        lambda series: series.rolling(KD_LOOKBACK, min_periods=1).max()
    )
    price_span = rolling_high - rolling_low
    data["kd_rsv9"] = (
        _safe_div((data["close"] - rolling_low) * 100.0, price_span)
        .fillna(50.0)
        .clip(0.0, 100.0)
    )

    kd_parts = [
        _smoothed_kd(group["kd_rsv9"])
        for _, group in data.groupby("stock_id", sort=False)
    ]
    kd = pd.concat(kd_parts).sort_index()
    data["kd_k9"] = kd["kd_k9"]
    data["kd_d9"] = kd["kd_d9"]
    data["kd_prev_k9"] = grouped["kd_k9"].shift(1)
    data["kd_prev_d9"] = grouped["kd_d9"].shift(1)
    data["kd_oversold_marker"] = data["kd_k9"] < KD_OVERSOLD_LEVEL
    data["kd_recent_oversold"] = grouped["kd_oversold_marker"].transform(
        lambda series: (
            series.shift(1)
            .rolling(KD_RECENT_OVERSOLD_WINDOW, min_periods=1)
            .max()
            .fillna(False)
            .astype(bool)
        )
    )
    data["kd_k_rising"] = data["kd_k9"] > data["kd_prev_k9"]
    data["kd_above_d"] = data["kd_k9"] > data["kd_d9"]
    data["kd_bull_cross"] = (
        data["kd_above_d"]
        & (data["kd_prev_k9"] <= data["kd_prev_d9"])
    )
    data["kd_recent_bull_cross"] = grouped["kd_bull_cross"].transform(
        lambda series: (
            series.rolling(KD_RECENT_OVERSOLD_WINDOW, min_periods=1)
            .max()
            .fillna(False)
            .astype(bool)
        )
    )


def _smoothed_kd(rsv: pd.Series) -> pd.DataFrame:
    k_previous = 50.0
    d_previous = 50.0
    k_values: list[float] = []
    d_values: list[float] = []
    for value in pd.to_numeric(rsv, errors="coerce").fillna(50.0):
        k_current = ((KD_SMOOTHING - 1) * k_previous + float(value)) / KD_SMOOTHING
        d_current = ((KD_SMOOTHING - 1) * d_previous + k_current) / KD_SMOOTHING
        k_values.append(k_current)
        d_values.append(d_current)
        k_previous = k_current
        d_previous = d_current
    return pd.DataFrame({"kd_k9": k_values, "kd_d9": d_values}, index=rsv.index)


def _add_price_zone_source_features(data: pd.DataFrame) -> None:
    grouped = data.groupby("stock_id", group_keys=False, sort=False)
    data["high_volume_red_k_low"] = data["low"].where(data["long_red_k"] & data["volume_expansion"])
    data["long_lower_shadow_low"] = data["low"].where(
        data["hammer_like"]
        | (
            (data["lower_shadow_pct"] > data["upper_shadow_pct"])
            & (data["close_position_in_range"] > 0.5)
        )
    )
    data["high_volume_black_k_high"] = data["high"].where(data["long_black_k"] & data["volume_expansion"])
    data["long_upper_shadow_high"] = data["high"].where(
        data["shooting_star_like"] | data["high_volume_upper_shadow"]
    )
    data["gap_up_support"] = data["prev_high"].where(data["gap_up"])
    data["gap_down_resistance"] = data["prev_low"].where(data["gap_down"])
    for column in [
        "high_volume_red_k_low",
        "long_lower_shadow_low",
        "high_volume_black_k_high",
        "long_upper_shadow_high",
        "gap_up_support",
        "gap_down_resistance",
    ]:
        data[column] = grouped[column].ffill()


def _add_state_labels(data: pd.DataFrame) -> None:
    trend_conditions = [
        data["close"] < data["prev_low_20d"],
        data["ma_bear_alignment"],
        data["ma_bull_alignment"] & (data["ma5_slope"] > 0) & (data["ma10_slope"] > 0),
        ((data["close"] < data["ma5"]) | (data["close"] < data["ma10"])) & (data["close"] > data["ma60"]),
        (data["return_1d"] > 0) & (data["close"] < data["ma10"]),
    ]
    data["trend_state"] = np.select(
        trend_conditions,
        ["BREAKDOWN", "DOWNTREND", "UPTREND", "PULLBACK_IN_UPTREND", "WEAK_REBOUND"],
        default="RANGE_BOUND",
    )

    data["ma_state"] = np.select(
        [
            data["ma_bull_alignment"],
            data["ma_reclaim_5"] | data["ma_reclaim_10"] | data["ma_reclaim_20"],
            data["ma_compression"],
            data["ma_break_5"] | data["ma_break_10"] | data["ma_break_20"],
            data["ma_bear_alignment"],
        ],
        ["BULL_ALIGNMENT", "MA_RECLAIM", "MA_COMPRESSION", "MA_BREAK", "BEAR_ALIGNMENT"],
        default="BULL_PULLBACK",
    )

    data["kline_state"] = np.select(
        [
            data["long_red_k"] & data["close_above_prev_high"],
            data["hammer_like"] | data["failed_breakdown"],
            data["red_k"] & (data["vol_ratio_20"] < 1.0),
            data["long_black_k"],
            data["high_volume_upper_shadow"] | data["shooting_star_like"],
            data["close_below_prev_low"],
        ],
        [
            "ATTACK_RED_K",
            "STOPPING_K",
            "WEAK_REBOUND_K",
            "LONG_BLACK_K",
            "UPPER_SHADOW_SUPPLY",
            "BREAKDOWN_K",
        ],
        default="RANGE_K",
    )

    data["volume_state"] = np.select(
        [
            data["price_up_volume_up"],
            data["low_volume_pullback"],
            data["price_up_volume_down"],
            data["high_volume_long_black"] | data["high_volume_upper_shadow"],
            data["price_down_volume_up"],
        ],
        [
            "ATTACK_VOLUME",
            "HEALTHY_PULLBACK_VOLUME",
            "WEAK_REBOUND_VOLUME",
            "DISTRIBUTION_VOLUME",
            "PANIC_VOLUME",
        ],
        default="NEUTRAL_VOLUME",
    )


def _add_support_resistance(latest: pd.DataFrame) -> None:
    supports: list[list[dict[str, object]]] = []
    resistances: list[list[dict[str, object]]] = []
    broken_supports: list[dict[str, object] | None] = []
    breakout_zones: list[dict[str, object] | None] = []
    for _, row in latest.iterrows():
        close = float(row["close"])
        support_candidates = _price_candidates(
            [
                (row.get("prev_low"), "prev_low"),
                (row.get("swing_low_3d"), "swing_low_3d"),
                (row.get("swing_low_1"), "swing_low_5d"),
                (row.get("swing_low_2"), "swing_low_20d"),
                (row.get("low_20d"), "low_20d"),
                (row.get("low_60d"), "low_60d"),
                (row.get("ma5"), "ma5"),
                (row.get("ma10"), "ma10"),
                (row.get("ma20"), "ma20"),
                (row.get("ma60"), "ma60"),
                (row.get("high_volume_red_k_low"), "high_volume_red_k_low"),
                (row.get("long_lower_shadow_low"), "long_lower_shadow_low"),
                (row.get("gap_up_support"), "gap_up_support"),
                *_round_number_candidates(close, side="support"),
            ]
        )
        resistance_candidates = _price_candidates(
            [
                (row.get("prev_high"), "prev_high"),
                (row.get("swing_high_3d"), "swing_high_3d"),
                (row.get("swing_high_1"), "swing_high_5d"),
                (row.get("swing_high_2"), "swing_high_20d"),
                (row.get("high_20d"), "high_20d"),
                (row.get("high_60d"), "high_60d"),
                (row.get("ma5"), "ma5"),
                (row.get("ma10"), "ma10"),
                (row.get("ma20"), "ma20"),
                (row.get("ma60"), "ma60"),
                (row.get("high_volume_black_k_high"), "high_volume_black_k_high"),
                (row.get("long_upper_shadow_high"), "long_upper_shadow_high"),
                (row.get("gap_down_resistance"), "gap_down_resistance"),
                *_round_number_candidates(close, side="resistance"),
            ]
        )
        support_clusters = _cluster_price_zones(support_candidates)
        resistance_clusters = _cluster_price_zones(resistance_candidates)
        supports.append(_select_price_zones(support_clusters, close, side="support"))
        resistances.append(_select_price_zones(resistance_clusters, close, side="resistance"))
        broken_supports.append(_nearest_zone_above(support_clusters, close))
        breakout_zones.append(_nearest_zone_below(resistance_clusters, close))

    for idx in range(MAX_PRICE_ZONES):
        number = idx + 1
        for side, zones in [("support", supports), ("resistance", resistances)]:
            latest[f"{side}_zone_{number}_low"] = _zone_field_values(zones, idx, "low", np.nan)
            latest[f"{side}_zone_{number}_high"] = _zone_field_values(zones, idx, "high", np.nan)
            latest[f"{side}_zone_{number}_mid"] = _zone_field_values(zones, idx, "mid", np.nan)
            latest[f"{side}_zone_{number}_sources"] = _zone_field_values(zones, idx, "sources", "")
        latest[f"support_{number}"] = latest[f"support_zone_{number}_low"]
        latest[f"resistance_{number}"] = latest[f"resistance_zone_{number}_high"]

    for prefix, zones in [("broken_support_zone", broken_supports), ("breakout_zone", breakout_zones)]:
        latest[f"{prefix}_low"] = [zone["low"] if zone is not None else np.nan for zone in zones]
        latest[f"{prefix}_high"] = [zone["high"] if zone is not None else np.nan for zone in zones]
        latest[f"{prefix}_sources"] = [zone["sources"] if zone is not None else "" for zone in zones]

    latest["nearest_support_distance"] = _safe_div(
        latest["close"] - latest["support_zone_1_high"], latest["close"]
    )
    latest["nearest_resistance_distance"] = _safe_div(
        latest["resistance_zone_1_low"] - latest["close"], latest["close"]
    )
    latest["risk_reward_proxy"] = _safe_div(
        latest["nearest_resistance_distance"], latest["nearest_support_distance"].abs()
    )
    latest["support_zone_holding_today"] = (
        (latest["close"] >= latest["support_zone_1_low"])
        & (latest["low"] <= latest["support_zone_1_high"])
        & (latest["close_position_in_range"] > 0.5)
        & (latest["lower_shadow_pct"] > latest["upper_shadow_pct"])
        & (~latest["high_volume_long_black"].fillna(False))
    )
    latest["support_zone_failed_today"] = (
        (latest["close"] < latest["broken_support_zone_low"])
        | latest["close_below_prev_low"].fillna(False)
        | latest["price_down_volume_up"].fillna(False)
    )
    latest["resistance_zone_breakout_today"] = (
        latest["breakout_zone_high"].notna()
        & (latest["prev_close"] <= latest["breakout_zone_high"])
        & (latest["close"] > latest["breakout_zone_high"])
        & ((latest["volume"] > latest["vol_ma5"]) | (latest["volume"] > latest["vol_ma20"]))
        & (latest["close_position_in_range"] > 0.6)
        & (~latest["high_volume_upper_shadow"].fillna(False))
    )
    latest["resistance_zone_breakout_failed_today"] = (
        latest["resistance_zone_1_high"].notna()
        & (latest["high"] > latest["resistance_zone_1_high"])
        & (latest["close"] < latest["resistance_zone_1_high"])
        & (latest["upper_shadow_pct"] >= 0.025)
        & (latest["volume"] > latest["vol_ma20"])
    )
    latest["support_broken_today"] = latest["support_zone_failed_today"] | (
        latest["close"] < latest["ma20"]
    )
    latest["resistance_reclaimed_today"] = (
        latest["close_above_prev_high"]
        | latest["ma_reclaim_20"]
        | latest["resistance_zone_breakout_today"]
    )
    latest["support_zone_1_label"] = latest.apply(
        lambda row: _zone_label(row.get("support_zone_1_low"), row.get("support_zone_1_high")),
        axis=1,
    )
    latest["resistance_zone_1_label"] = latest.apply(
        lambda row: _zone_label(row.get("resistance_zone_1_low"), row.get("resistance_zone_1_high")),
        axis=1,
    )
    latest["stop_reference"] = latest.apply(
        lambda row: (
            ""
            if pd.isna(row.get("support_zone_1_low"))
            else f"跌破支撐區 {row['support_zone_1_label']} 重新評估"
        ),
        axis=1,
    )
    latest["entry_observation"] = latest.apply(_entry_observation, axis=1)


def _add_kd_observation_features(latest: pd.DataFrame) -> None:
    """Confirm KD recovery only after price, trend, and strength gates pass."""
    close = pd.to_numeric(latest["close"], errors="coerce")
    ma20 = pd.to_numeric(latest["ma20"], errors="coerce")
    ma60 = pd.to_numeric(latest["ma60"], errors="coerce")
    ma120 = pd.to_numeric(latest["ma120"], errors="coerce")
    ma20_slope = pd.to_numeric(latest["ma20_slope"], errors="coerce")
    ma60_slope = pd.to_numeric(latest["ma60_slope"], errors="coerce")
    return_20d = pd.to_numeric(latest["return_20d"], errors="coerce")

    latest["kd_price_reclaim"] = latest["resistance_reclaimed_today"].fillna(False).astype(bool)
    latest["bull_trend_gate"] = (
        ~latest["trend_state"].isin({"DOWNTREND", "BREAKDOWN", "WEAK_REBOUND"})
        & (ma20_slope > 0)
        & (ma60_slope > 0)
        & (close > ma60)
    ).fillna(False)
    latest["strong_stock_gate"] = (
        (close > ma20)
        & (close > ma120)
        & (return_20d > 0)
    ).fillna(False)
    latest["kd_reclaim_price"] = latest.apply(_kd_reclaim_price, axis=1)
    supply_clear = ~latest["high_volume_upper_shadow"].fillna(False).astype(bool)
    tight_low_volume_gate = (
        latest["kd_prior_5d_tight_low_volume_gate"].fillna(False).astype(bool)
    )
    latest["kd_recovery_confirmation"] = (
        latest["kd_recent_oversold"].fillna(False).astype(bool)
        & latest["kd_k_rising"].fillna(False).astype(bool)
        & latest["kd_above_d"].fillna(False).astype(bool)
        & latest["kd_recent_bull_cross"].fillna(False).astype(bool)
        & latest["kd_price_reclaim"]
        & latest["bull_trend_gate"]
        & latest["strong_stock_gate"]
        & supply_clear
        & tight_low_volume_gate
    )
    latest["kd_observation_stage"] = np.select(
        [
            latest["kd_recovery_confirmation"],
            latest["kd_oversold_marker"].fillna(False),
            latest["kd_recent_oversold"].fillna(False) & ~latest["kd_k_rising"].fillna(False),
            latest["kd_recent_oversold"].fillna(False)
            & (
                ~latest["kd_above_d"].fillna(False)
                | ~latest["kd_recent_bull_cross"].fillna(False)
            ),
            latest["kd_recent_oversold"].fillna(False) & ~latest["kd_price_reclaim"],
            latest["kd_recent_oversold"].fillna(False)
            & latest["kd_price_reclaim"]
            & ~(latest["bull_trend_gate"] & latest["strong_stock_gate"]),
            latest["kd_recent_oversold"].fillna(False) & ~supply_clear,
            latest["kd_recent_oversold"].fillna(False) & ~tight_low_volume_gate,
        ],
        [
            "CONFIRMED",
            "OVERSOLD_ONLY",
            "WAIT_K_TURN",
            "WAIT_KD_CROSS",
            "WAIT_PRICE_RECLAIM",
            "WAIT_TREND_STRENGTH",
            "WAIT_SUPPLY_CLEAR",
            "WAIT_TIGHT_LOW_VOLUME",
        ],
        default="EMPTY",
    )
    latest["kd_observation_type"] = np.where(
        latest["kd_recovery_confirmation"],
        "KD_OVERSOLD_TREND_RECOVERY",
        "",
    )


def _kd_reclaim_price(row: pd.Series) -> float:
    candidates: tuple[str, ...]
    if bool(row.get("resistance_zone_breakout_today", False)):
        candidates = ("breakout_zone_high", "prev_high", "ma20")
    elif bool(row.get("close_above_prev_high", False)):
        candidates = ("prev_high", "ma20")
    elif bool(row.get("ma_reclaim_20", False)):
        candidates = ("ma20",)
    else:
        return np.nan
    values = _finite_values(row.get(column) for column in candidates)
    return float(values[0]) if values else np.nan


def _entry_observation(row: pd.Series) -> str:
    if bool(row.get("resistance_zone_breakout_today", False)):
        return f"觀察站穩壓力區 {row.get('resistance_zone_1_label', '')} 後的量價延續"
    if bool(row.get("resistance_reclaimed_today", False)):
        return "觀察站穩前高、壓力區或關鍵均線後的量價延續"
    if row.get("trend_state") == "PULLBACK_IN_UPTREND":
        return "觀察拉回守住20日線後是否重新放量"
    return "等待收過壓力或重新站回短均線"


def _price_candidates(values: Iterable[tuple[object, str]]) -> list[tuple[float, str]]:
    result: list[tuple[float, str]] = []
    for value, source in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number) and number > 0:
            result.append((round(number, 4), source))
    return result


def _zone_field_values(
    zones_by_row: list[list[dict[str, object]]],
    idx: int,
    field: str,
    default: object,
) -> list[object]:
    return [values[idx][field] if len(values) > idx else default for values in zones_by_row]


def _round_number_candidates(close: float, *, side: str) -> list[tuple[float, str]]:
    if not np.isfinite(close) or close <= 0:
        return []
    if close >= 1000:
        step = 50.0
    elif close >= 100:
        step = 5.0
    elif close >= 10:
        step = 1.0
    else:
        step = 0.5
    base = np.floor(close / step) * step
    offsets = range(-2, 1) if side == "support" else range(0, 3)
    return [(base + step * offset, "round_number") for offset in offsets if base + step * offset > 0]


def _cluster_price_zones(candidates: list[tuple[float, str]]) -> list[dict[str, object]]:
    clusters: list[dict[str, object]] = []
    for price, source in sorted(candidates, key=lambda item: item[0]):
        if not clusters or not _is_price_inside_cluster(price, clusters[-1]):
            clusters.append({"prices": [price], "sources": {source}})
            continue
        clusters[-1]["prices"].append(price)
        clusters[-1]["sources"].add(source)
    zones: list[dict[str, object]] = []
    for cluster in clusters:
        prices = [float(value) for value in cluster["prices"]]
        low = round(min(prices), 4)
        high = round(max(prices), 4)
        zones.append(
            {
                "low": low,
                "high": high,
                "mid": round((low + high) / 2.0, 4),
                "sources": "|".join(sorted(cluster["sources"])),
            }
        )
    return zones


def _is_price_inside_cluster(price: float, cluster: dict[str, object]) -> bool:
    prices = [float(value) for value in cluster["prices"]]
    midpoint = sum(prices) / len(prices)
    if midpoint <= 0:
        return False
    return abs(price - midpoint) / midpoint <= ZONE_MERGE_PCT


def _select_price_zones(
    zones: list[dict[str, object]],
    close: float,
    *,
    side: str,
) -> list[dict[str, object]]:
    if side == "support":
        selected = [zone for zone in zones if float(zone["mid"]) <= close]
        return sorted(selected, key=lambda zone: float(zone["high"]), reverse=True)[:MAX_PRICE_ZONES]
    selected = [zone for zone in zones if float(zone["mid"]) >= close]
    return sorted(selected, key=lambda zone: float(zone["low"]))[:MAX_PRICE_ZONES]


def _nearest_zone_above(zones: list[dict[str, object]], close: float) -> dict[str, object] | None:
    selected = [zone for zone in zones if float(zone["low"]) > close]
    if not selected:
        return None
    return sorted(selected, key=lambda zone: float(zone["low"]))[0]


def _nearest_zone_below(zones: list[dict[str, object]], close: float) -> dict[str, object] | None:
    selected = [zone for zone in zones if float(zone["high"]) < close]
    if not selected:
        return None
    return sorted(selected, key=lambda zone: float(zone["high"]), reverse=True)[0]


def _zone_label(low: object, high: object) -> str:
    if pd.isna(low) or pd.isna(high):
        return ""
    low_float = float(low)
    high_float = float(high)
    if abs(low_float - high_float) <= 1e-8:
        return f"{low_float:.2f}"
    return f"{low_float:.2f}~{high_float:.2f}"


def _finite_values(values: Iterable[object]) -> list[float]:
    result: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number) and number > 0:
            result.append(number)
    return result


def _safe_div(left: pd.Series | float, right: pd.Series | float) -> pd.Series:
    result = pd.Series(left) / pd.Series(right).replace(0.0, np.nan)
    return result.replace([np.inf, -np.inf], np.nan)
