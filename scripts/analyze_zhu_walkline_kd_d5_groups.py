"""Analyze Zhu walkline KD confirmation events by adjusted D+5 close return.

This evaluator-only sidecar reads already-generated shadow observation events.
Future prices are attached only after signal generation and never feed back into
features, signal stages, formal strategy state, positions, or orders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

GROUP_DEFINITIONS = [
    ("D5_LOSS", "D+5 < 0%", float("-inf"), 0.0, 1),
    ("D5_GAIN_10_20", "D+5 +10% to <20%", 10.0, 20.0, 2),
    ("D5_GAIN_GE_20", "D+5 >=20%", 20.0, float("inf"), 3),
]
D5_BOUNDARY_TOLERANCE_PCT = 1e-9

DAILY_FEATURE_COLUMNS = [
    "date",
    "stock_id",
    "open",
    "high",
    "low",
    "volume",
    "previous_close",
    "overnight_return",
    "intraday_return",
    "open_to_close_pct",
    "gap_up_pct",
    "close_from_high_pct",
    "low_from_open_pct",
    "close_location_in_bar",
    "range_pos_20",
    "sma5",
    "sma10",
    "sma20",
    "sma60",
    "sma5_gap",
    "sma10_gap",
    "sma20_gap",
    "sma60_gap",
    "volume_ma5",
    "volume_ma20",
    "volume_ratio_5_20",
    "day_volume_ratio_20",
    "overnight_return_rankpct",
    "intraday_return_rankpct",
    "sma20_gap_rankpct",
    "day_volume_ratio_20_rankpct",
    "range_pos_20_rankpct",
    "close_from_high_rankpct",
    "gap_reversal_flag",
    "upper_tail_flag",
    "volume_exhaustion_flag",
    "late_chase_risk_flag",
]

NUMERIC_FEATURES = [
    "kd_k9",
    "kd_d9",
    "kd_spread",
    "return_20d_pct",
    "ma20_slope_pct",
    "ma60_slope_pct",
    "close_to_ma20_pct",
    "close_to_ma60_pct",
    "close_to_ma120_pct",
    "invalidation_distance_pct",
    "confirmation_distance_pct",
    "overnight_return",
    "intraday_return",
    "open_to_close_pct",
    "gap_up_pct",
    "close_from_high_pct",
    "low_from_open_pct",
    "close_location_in_bar",
    "range_pos_20",
    "sma5_gap",
    "sma10_gap",
    "sma20_gap",
    "sma60_gap",
    "volume_ratio_5_20",
    "day_volume_ratio_20",
    "turnover_million_twd",
    "overnight_return_rankpct",
    "intraday_return_rankpct",
    "sma20_gap_rankpct",
    "day_volume_ratio_20_rankpct",
    "range_pos_20_rankpct",
    "close_from_high_rankpct",
]

CATEGORICAL_FEATURES = [
    "sector",
    "trend_state",
    "signal_month",
    "signal_k_direction",
    "close_location_bucket",
    "volume_ratio_bucket",
    "ma20_extension_bucket",
    "kd_k_bucket",
    "gap_reversal_flag",
    "upper_tail_flag",
    "volume_exhaustion_flag",
    "late_chase_risk_flag",
]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_csv = REPO_ROOT / args.input_csv
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])

    events = pd.read_csv(input_csv, dtype={"stock_id": str})
    events = _filter_events(events, start_date=args.start_date, end_date=args.end_date)
    adjusted_prices = load_adjusted_prices(
        events,
        sqlite_path=sqlite_path,
        horizon_trading_days=args.horizon_trading_days,
    )
    daily_features = load_daily_features(events, sqlite_path=sqlite_path)
    analysis = build_kd_d5_group_analysis(
        events,
        adjusted_prices=adjusted_prices,
        daily_features=daily_features,
        horizon_trading_days=args.horizon_trading_days,
        min_category_count=args.min_category_count,
    )
    write_outputs(analysis, output_dir=output_dir, args=args)

    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"labeled_rows_csv={output_dir / 'zhu_walkline_kd_d5_labeled_rows.csv'}")
    print(f"group_summary_csv={output_dir / 'zhu_walkline_kd_d5_group_summary.csv'}")
    print(f"numeric_features_csv={output_dir / 'zhu_walkline_kd_d5_numeric_features.csv'}")
    print(f"categorical_lift_csv={output_dir / 'zhu_walkline_kd_d5_categorical_lift.csv'}")
    print(f"pairwise_numeric_csv={output_dir / 'zhu_walkline_kd_d5_pairwise_numeric.csv'}")
    print(
        f"pairwise_categorical_csv="
        f"{output_dir / 'zhu_walkline_kd_d5_pairwise_categorical.csv'}"
    )
    print(f"top_drivers_csv={output_dir / 'zhu_walkline_kd_d5_top_drivers.csv'}")
    print(
        f"unique_stock_summary_csv="
        f"{output_dir / 'zhu_walkline_kd_d5_unique_stock_summary.csv'}"
    )
    print(f"summary_json={output_dir / 'zhu_walkline_kd_d5_summary.json'}")
    print(f"summary_md={output_dir / 'zhu_walkline_kd_d5_summary.md'}")
    return 0


def build_kd_d5_group_analysis(
    events: pd.DataFrame,
    *,
    adjusted_prices: pd.DataFrame,
    daily_features: pd.DataFrame,
    horizon_trading_days: int = 5,
    min_category_count: int = 10,
) -> dict[str, Any]:
    labeled = attach_d5_labels(
        events,
        adjusted_prices=adjusted_prices,
        horizon_trading_days=horizon_trading_days,
    )
    labeled = enrich_signal_features(labeled, daily_features=daily_features)
    labeled["d5_group"] = labeled["d5_adjusted_return_pct"].map(assign_d5_group)
    labeled["d5_group_label"] = labeled["d5_group"].map(
        {key: label for key, label, *_ in GROUP_DEFINITIONS}
    ).fillna("UNGROUPED_0_TO_LT10")
    labeled["d5_group_order"] = labeled["d5_group"].map(
        {key: order for key, _label, _lower, _upper, order in GROUP_DEFINITIONS}
    ).fillna(0).astype(int)
    labeled.loc[~labeled["label_mature"], "d5_group_label"] = "MISSING_D5_LABEL"
    labeled.loc[~labeled["label_mature"], "d5_group_order"] = -1

    grouped = labeled[labeled["d5_group"].ne("") & labeled["label_mature"]].copy()
    ungrouped = labeled[labeled["d5_group"].eq("") & labeled["label_mature"]].copy()
    cooldown = apply_same_stock_cooldown(grouped, horizon_trading_days=horizon_trading_days)
    no_actions = grouped[
        ~grouped["corporate_action_event_in_horizon"].fillna(False).astype(bool)
    ].copy()

    summary_frames = [
        compute_group_summary(grouped, scope="all_events"),
        compute_group_summary(cooldown, scope="same_stock_5d_cooldown"),
        compute_group_summary(no_actions, scope="no_corporate_action"),
    ]
    group_summary = pd.concat(summary_frames, ignore_index=True)
    numeric_features = compute_numeric_feature_stats(grouped)
    categorical_lift = compute_categorical_lift(
        grouped,
        min_count=min_category_count,
    )
    pairwise_numeric = pd.concat(
        [
            compute_pairwise_numeric_contrasts(grouped, scope="all_events"),
            compute_pairwise_numeric_contrasts(
                cooldown,
                scope="same_stock_5d_cooldown",
            ),
            compute_pairwise_numeric_contrasts(
                no_actions,
                scope="no_corporate_action",
            ),
        ],
        ignore_index=True,
    )
    pairwise_categorical = compute_pairwise_categorical_contrasts(
        grouped,
        min_count=min_category_count,
    )
    top_drivers = compute_top_drivers(
        numeric_features=numeric_features,
        categorical_lift=categorical_lift,
        min_count=min_category_count,
    )
    unique_stock_summary = compute_unique_stock_summary(grouped)
    summary = build_summary_payload(
        labeled=labeled,
        grouped=grouped,
        ungrouped=ungrouped,
        cooldown=cooldown,
        no_actions=no_actions,
        group_summary=group_summary,
        top_drivers=top_drivers,
        horizon_trading_days=horizon_trading_days,
        min_category_count=min_category_count,
        adjusted_prices=adjusted_prices,
    )
    return {
        "labeled_rows": labeled,
        "grouped_rows": grouped,
        "ungrouped_rows": ungrouped,
        "cooldown_rows": cooldown,
        "no_corporate_action_rows": no_actions,
        "group_summary": group_summary,
        "numeric_features": numeric_features,
        "categorical_lift": categorical_lift,
        "pairwise_numeric": pairwise_numeric,
        "pairwise_categorical": pairwise_categorical,
        "top_drivers": top_drivers,
        "unique_stock_summary": unique_stock_summary,
        "summary": summary,
    }


def assign_d5_group(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return ""
    if number < -D5_BOUNDARY_TOLERANCE_PCT:
        return "D5_LOSS"
    if number < 10.0 - D5_BOUNDARY_TOLERANCE_PCT:
        return ""
    if number < 20.0 - D5_BOUNDARY_TOLERANCE_PCT:
        return "D5_GAIN_10_20"
    return "D5_GAIN_GE_20"


def attach_d5_labels(
    events: pd.DataFrame,
    *,
    adjusted_prices: pd.DataFrame,
    horizon_trading_days: int = 5,
) -> pd.DataFrame:
    if horizon_trading_days < 1:
        raise ValueError("horizon_trading_days must be positive")
    output = events.copy()
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["asof_date"] = pd.to_datetime(output["asof_date"]).dt.strftime("%Y-%m-%d")
    if adjusted_prices.empty:
        return _add_empty_label_columns(output)

    prices = adjusted_prices.copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    prices = prices.dropna(subset=["date", "stock_id"]).sort_values(["stock_id", "date"])
    prices = prices.drop_duplicates(["stock_id", "date"], keep="last").reset_index(drop=True)
    for column in ["close", "adj_close", "adjustment_factor", "factor_event_count"]:
        prices[column] = pd.to_numeric(prices.get(column), errors="coerce")
    grouped = prices.groupby("stock_id", group_keys=False, sort=False)
    labels = prices[
        ["date", "stock_id", "close", "adj_close", "adjustment_factor", "adjusted_data_asof"]
    ].copy()
    labels = labels.rename(
        columns={
            "date": "asof_date",
            "close": "signal_raw_close",
            "adj_close": "signal_adj_close",
            "adjustment_factor": "signal_adjustment_factor",
        }
    )
    labels["signal_trade_index"] = grouped.cumcount().astype(int)
    labels["d5_close_date"] = grouped["date"].shift(-horizon_trading_days)
    labels["d5_raw_close"] = grouped["close"].shift(-horizon_trading_days)
    labels["d5_adj_close"] = grouped["adj_close"].shift(-horizon_trading_days)
    labels["d5_adjustment_factor"] = grouped["adjustment_factor"].shift(
        -horizon_trading_days
    )
    labels["d5_factor_event_count"] = grouped["factor_event_count"].shift(
        -horizon_trading_days
    )
    labels["asof_date"] = labels["asof_date"].dt.strftime("%Y-%m-%d")

    output = output.merge(labels, on=["asof_date", "stock_id"], how="left")
    signal_adj = pd.to_numeric(output["signal_adj_close"], errors="coerce")
    d5_adj = pd.to_numeric(output["d5_adj_close"], errors="coerce")
    signal_raw = pd.to_numeric(output["signal_raw_close"], errors="coerce")
    d5_raw = pd.to_numeric(output["d5_raw_close"], errors="coerce")
    output["d5_adjusted_return_pct"] = ((d5_adj / signal_adj) - 1.0) * 100.0
    output["d5_raw_return_pct"] = ((d5_raw / signal_raw) - 1.0) * 100.0
    output["raw_adjusted_return_gap_pct"] = (
        output["d5_raw_return_pct"] - output["d5_adjusted_return_pct"]
    )
    signal_factor = pd.to_numeric(output["signal_adjustment_factor"], errors="coerce")
    d5_factor = pd.to_numeric(output["d5_adjustment_factor"], errors="coerce")
    output["corporate_action_event_in_horizon"] = (
        signal_factor.notna()
        & d5_factor.notna()
        & ((signal_factor - d5_factor).abs() > 1e-12)
    )
    output["label_mature"] = signal_adj.notna() & d5_adj.notna()
    output["d5_close_date"] = pd.to_datetime(
        output["d5_close_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    return output


def enrich_signal_features(
    labeled: pd.DataFrame,
    *,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    output = labeled.copy()
    if not daily_features.empty:
        features = daily_features.copy()
        features["stock_id"] = features["stock_id"].astype(str).str.zfill(4)
        features["asof_date"] = pd.to_datetime(features["date"]).dt.strftime("%Y-%m-%d")
        features = features.drop(columns=["date"])
        duplicates = [column for column in features.columns if column in output.columns]
        features = features.rename(columns={column: f"daily_{column}" for column in duplicates})
        features = features.rename(
            columns={"daily_stock_id": "stock_id", "daily_asof_date": "asof_date"}
        )
        output = output.merge(features, on=["asof_date", "stock_id"], how="left")

    close = pd.to_numeric(output.get("close"), errors="coerce")
    output["kd_spread"] = pd.to_numeric(output.get("kd_k9"), errors="coerce") - pd.to_numeric(
        output.get("kd_d9"), errors="coerce"
    )
    output["return_20d_pct"] = pd.to_numeric(output.get("return_20d"), errors="coerce") * 100.0
    output["ma20_slope_pct"] = _safe_pct(output.get("ma20_slope"), output.get("ma20"))
    output["ma60_slope_pct"] = _safe_pct(output.get("ma60_slope"), output.get("ma60"))
    output["close_to_ma20_pct"] = _safe_gap_pct(close, output.get("ma20"))
    output["close_to_ma60_pct"] = _safe_gap_pct(close, output.get("ma60"))
    output["close_to_ma120_pct"] = _safe_gap_pct(close, output.get("ma120"))
    output["invalidation_distance_pct"] = _safe_gap_pct(
        close, output.get("invalid_price")
    )
    output["confirmation_distance_pct"] = _safe_gap_pct(
        output.get("confirm_price"), close
    )
    volume = pd.to_numeric(output.get("volume"), errors="coerce")
    output["turnover_million_twd"] = close * volume / 1_000_000.0
    output["signal_month"] = output["asof_date"].astype(str).str.slice(0, 7)

    open_price = pd.to_numeric(output.get("open"), errors="coerce")
    output["signal_k_direction"] = np.select(
        [close > open_price, close < open_price],
        ["RED_K", "BLACK_K"],
        default="FLAT_K",
    )
    output["close_location_bucket"] = pd.cut(
        pd.to_numeric(output.get("close_location_in_bar"), errors="coerce"),
        bins=[-np.inf, 0.3, 0.7, np.inf],
        labels=["LOW_CLOSE", "MID_CLOSE", "HIGH_CLOSE"],
        right=False,
    ).astype("string")
    output["volume_ratio_bucket"] = pd.cut(
        pd.to_numeric(output.get("day_volume_ratio_20"), errors="coerce"),
        bins=[-np.inf, 0.75, 1.3, 2.0, np.inf],
        labels=["LOW_VOLUME", "NORMAL_VOLUME", "EXPANDED_VOLUME", "EXTREME_VOLUME"],
        right=False,
    ).astype("string")
    output["ma20_extension_bucket"] = pd.cut(
        output["close_to_ma20_pct"],
        bins=[-np.inf, 0.0, 5.0, 10.0, np.inf],
        labels=["AT_OR_BELOW_MA20", "MA20_PLUS_0_5", "MA20_PLUS_5_10", "MA20_PLUS_GE10"],
        right=False,
    ).astype("string")
    output["kd_k_bucket"] = pd.cut(
        pd.to_numeric(output.get("kd_k9"), errors="coerce"),
        bins=[-np.inf, 40.0, 60.0, np.inf],
        labels=["K_LT40", "K_40_60", "K_GE60"],
        right=False,
    ).astype("string")
    return output


def apply_same_stock_cooldown(
    rows: pd.DataFrame,
    *,
    horizon_trading_days: int,
) -> pd.DataFrame:
    if rows.empty:
        return rows.copy()
    kept_indices: list[int] = []
    ordered = rows.sort_values(["stock_id", "signal_trade_index", "asof_date"])
    for _stock_id, group in ordered.groupby("stock_id", sort=False):
        last_kept: int | None = None
        for index, row in group.iterrows():
            current = int(row["signal_trade_index"])
            if last_kept is None or current - last_kept > horizon_trading_days:
                kept_indices.append(index)
                last_kept = current
    return rows.loc[kept_indices].sort_values(["asof_date", "stock_id"]).reset_index(drop=True)


def compute_group_summary(rows: pd.DataFrame, *, scope: str) -> pd.DataFrame:
    columns = [
        "scope",
        "d5_group_order",
        "d5_group",
        "d5_group_label",
        "rows",
        "unique_stocks",
        "avg_d5_adjusted_return_pct",
        "median_d5_adjusted_return_pct",
        "q25_d5_adjusted_return_pct",
        "q75_d5_adjusted_return_pct",
        "corporate_action_event_rate",
    ]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    frame = (
        rows.groupby(["d5_group_order", "d5_group", "d5_group_label"], dropna=False)
        .agg(
            rows=("stock_id", "count"),
            unique_stocks=("stock_id", "nunique"),
            avg_d5_adjusted_return_pct=("d5_adjusted_return_pct", "mean"),
            median_d5_adjusted_return_pct=("d5_adjusted_return_pct", "median"),
            q25_d5_adjusted_return_pct=("d5_adjusted_return_pct", lambda s: s.quantile(0.25)),
            q75_d5_adjusted_return_pct=("d5_adjusted_return_pct", lambda s: s.quantile(0.75)),
            corporate_action_event_rate=("corporate_action_event_in_horizon", "mean"),
        )
        .reset_index()
        .sort_values("d5_group_order")
    )
    frame.insert(0, "scope", scope)
    return _round_numeric(frame)


def compute_numeric_feature_stats(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if rows.empty:
        return pd.DataFrame()
    order = pd.to_numeric(rows["d5_group_order"], errors="coerce")
    for feature in NUMERIC_FEATURES:
        if feature not in rows.columns:
            continue
        all_values = pd.to_numeric(rows[feature], errors="coerce")
        all_mean = all_values.mean()
        all_std = all_values.std(ddof=0)
        spearman = (
            all_values.rank(method="average").corr(order.rank(method="average"))
            if all_values.nunique(dropna=True) >= 2 and order.nunique(dropna=True) >= 2
            else 0.0
        )
        for group_key, group in rows.groupby("d5_group", sort=False):
            values = pd.to_numeric(group[feature], errors="coerce")
            mean = values.mean()
            records.append(
                {
                    "d5_group_order": int(group["d5_group_order"].iloc[0]),
                    "d5_group": group_key,
                    "d5_group_label": group["d5_group_label"].iloc[0],
                    "feature": feature,
                    "rows": int(values.notna().sum()),
                    "mean": mean,
                    "median": values.median(),
                    "q25": values.quantile(0.25),
                    "q75": values.quantile(0.75),
                    "all_grouped_mean": all_mean,
                    "mean_delta_vs_all": mean - all_mean,
                    "standardized_delta_vs_all": (
                        (mean - all_mean) / all_std
                        if all_std and pd.notna(all_std)
                        else 0.0
                    ),
                    "spearman_with_group_order": spearman,
                }
            )
    return _round_numeric(pd.DataFrame(records).sort_values(["d5_group_order", "feature"]))


def compute_categorical_lift(
    rows: pd.DataFrame,
    *,
    min_count: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if rows.empty:
        return pd.DataFrame()
    total = len(rows)
    for feature in CATEGORICAL_FEATURES:
        if feature not in rows.columns:
            continue
        all_values = rows[feature].fillna("").astype(str).str.strip()
        all_counts = all_values.value_counts()
        for group_key, group in rows.groupby("d5_group", sort=False):
            group_values = group[feature].fillna("").astype(str).str.strip()
            group_total = len(group)
            for value, count in group_values.value_counts().items():
                if not value or int(count) < min_count:
                    continue
                all_count = int(all_counts.get(value, 0))
                all_share = all_count / total
                group_share = int(count) / group_total
                records.append(
                    {
                        "d5_group_order": int(group["d5_group_order"].iloc[0]),
                        "d5_group": group_key,
                        "d5_group_label": group["d5_group_label"].iloc[0],
                        "feature": feature,
                        "value": value,
                        "count": int(count),
                        "group_rows": group_total,
                        "all_count": all_count,
                        "group_share": group_share,
                        "all_share": all_share,
                        "lift": group_share / all_share if all_share else 0.0,
                    }
                )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return _round_numeric(
        frame.sort_values(["d5_group_order", "lift", "count"], ascending=[True, False, False])
    )


def compute_pairwise_numeric_contrasts(
    rows: pd.DataFrame,
    *,
    scope: str,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    loss = rows[rows["d5_group"].eq("D5_LOSS")]
    if loss.empty:
        return pd.DataFrame()
    for target_key in ["D5_GAIN_10_20", "D5_GAIN_GE_20"]:
        target = rows[rows["d5_group"].eq(target_key)]
        if target.empty:
            continue
        for feature in NUMERIC_FEATURES:
            if feature not in rows.columns:
                continue
            target_values = pd.to_numeric(target[feature], errors="coerce").dropna()
            loss_values = pd.to_numeric(loss[feature], errors="coerce").dropna()
            if target_values.empty or loss_values.empty:
                continue
            pooled_std = np.sqrt(
                (target_values.var(ddof=0) + loss_values.var(ddof=0)) / 2.0
            )
            mean_diff = target_values.mean() - loss_values.mean()
            records.append(
                {
                    "scope": scope,
                    "target_group": target_key,
                    "target_group_label": target["d5_group_label"].iloc[0],
                    "reference_group": "D5_LOSS",
                    "feature": feature,
                    "target_rows": int(len(target_values)),
                    "reference_rows": int(len(loss_values)),
                    "target_mean": target_values.mean(),
                    "reference_mean": loss_values.mean(),
                    "target_median": target_values.median(),
                    "reference_median": loss_values.median(),
                    "mean_difference": mean_diff,
                    "standardized_mean_difference": (
                        mean_diff / pooled_std
                        if pooled_std and pd.notna(pooled_std)
                        else 0.0
                    ),
                }
            )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame["absolute_standardized_difference"] = frame[
        "standardized_mean_difference"
    ].abs()
    return _round_numeric(
        frame.sort_values(
            ["scope", "target_group", "absolute_standardized_difference"],
            ascending=[True, True, False],
        )
    )


def compute_pairwise_categorical_contrasts(
    rows: pd.DataFrame,
    *,
    min_count: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    loss = rows[rows["d5_group"].eq("D5_LOSS")]
    if loss.empty:
        return pd.DataFrame()
    for target_key in ["D5_GAIN_10_20", "D5_GAIN_GE_20"]:
        target = rows[rows["d5_group"].eq(target_key)]
        if target.empty:
            continue
        for feature in CATEGORICAL_FEATURES:
            if feature not in rows.columns:
                continue
            target_values = target[feature].fillna("").astype(str).str.strip()
            loss_values = loss[feature].fillna("").astype(str).str.strip()
            values = sorted(set(target_values.unique()) | set(loss_values.unique()))
            for value in values:
                if not value:
                    continue
                target_count = int(target_values.eq(value).sum())
                loss_count = int(loss_values.eq(value).sum())
                if target_count < min_count or loss_count < min_count:
                    continue
                target_share = target_count / len(target)
                loss_share = loss_count / len(loss)
                target_odds = (target_count + 0.5) / (len(target) - target_count + 0.5)
                loss_odds = (loss_count + 0.5) / (len(loss) - loss_count + 0.5)
                records.append(
                    {
                        "target_group": target_key,
                        "target_group_label": target["d5_group_label"].iloc[0],
                        "reference_group": "D5_LOSS",
                        "feature": feature,
                        "value": value,
                        "target_count": target_count,
                        "reference_count": loss_count,
                        "target_share": target_share,
                        "reference_share": loss_share,
                        "share_difference": target_share - loss_share,
                        "relative_rate": target_share / loss_share if loss_share else np.nan,
                        "odds_ratio": target_odds / loss_odds,
                    }
                )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame["absolute_share_difference"] = frame["share_difference"].abs()
    return _round_numeric(
        frame.sort_values(
            ["target_group", "absolute_share_difference"],
            ascending=[True, False],
        )
    )


def compute_top_drivers(
    *,
    numeric_features: pd.DataFrame,
    categorical_lift: pd.DataFrame,
    min_count: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if not numeric_features.empty:
        numeric = numeric_features[numeric_features["rows"].ge(min_count)].copy()
        numeric["driver_score"] = (
            numeric["standardized_delta_vs_all"].abs() * np.sqrt(numeric["rows"])
        )
        numeric = numeric.sort_values(
            ["d5_group_order", "driver_score"], ascending=[True, False]
        )
        for group_key, group in numeric.groupby("d5_group", sort=False):
            for _, row in group.head(10).iterrows():
                direction = "HIGH" if row["standardized_delta_vs_all"] > 0 else "LOW"
                records.append(
                    {
                        "d5_group_order": row["d5_group_order"],
                        "d5_group": group_key,
                        "d5_group_label": row["d5_group_label"],
                        "driver_type": "NUMERIC_EFFECT",
                        "driver": f"{direction}_{row['feature']}",
                        "count": row["rows"],
                        "effect_or_lift": row["standardized_delta_vs_all"],
                        "group_value": row["mean"],
                        "all_value": row["all_grouped_mean"],
                        "driver_score": row["driver_score"],
                    }
                )
    if not categorical_lift.empty:
        category = categorical_lift[
            categorical_lift["count"].ge(min_count) & categorical_lift["lift"].ge(1.1)
        ].copy()
        category["driver_score"] = category["lift"] * np.sqrt(category["count"])
        category = category.sort_values(
            ["d5_group_order", "driver_score"], ascending=[True, False]
        )
        for group_key, group in category.groupby("d5_group", sort=False):
            for _, row in group.head(10).iterrows():
                records.append(
                    {
                        "d5_group_order": row["d5_group_order"],
                        "d5_group": group_key,
                        "d5_group_label": row["d5_group_label"],
                        "driver_type": "CATEGORY_LIFT",
                        "driver": f"{row['feature']}={row['value']}",
                        "count": row["count"],
                        "effect_or_lift": row["lift"],
                        "group_value": row["group_share"],
                        "all_value": row["all_share"],
                        "driver_score": row["driver_score"],
                    }
                )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return _round_numeric(
        frame.sort_values(["d5_group_order", "driver_score"], ascending=[True, False])
    )


def compute_unique_stock_summary(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    frame = (
        rows.groupby(
            ["d5_group_order", "d5_group", "d5_group_label", "stock_id", "stock_name"],
            dropna=False,
        )
        .agg(
            sector=("sector", "first"),
            event_count=("asof_date", "count"),
            first_signal_date=("asof_date", "min"),
            last_signal_date=("asof_date", "max"),
            avg_d5_adjusted_return_pct=("d5_adjusted_return_pct", "mean"),
            median_d5_adjusted_return_pct=("d5_adjusted_return_pct", "median"),
            min_d5_adjusted_return_pct=("d5_adjusted_return_pct", "min"),
            max_d5_adjusted_return_pct=("d5_adjusted_return_pct", "max"),
        )
        .reset_index()
        .sort_values(
            ["d5_group_order", "avg_d5_adjusted_return_pct", "stock_id"],
            ascending=[True, False, True],
        )
    )
    return _round_numeric(frame)


def build_summary_payload(
    *,
    labeled: pd.DataFrame,
    grouped: pd.DataFrame,
    ungrouped: pd.DataFrame,
    cooldown: pd.DataFrame,
    no_actions: pd.DataFrame,
    group_summary: pd.DataFrame,
    top_drivers: pd.DataFrame,
    horizon_trading_days: int,
    min_category_count: int,
    adjusted_prices: pd.DataFrame,
) -> dict[str, Any]:
    mature = labeled[labeled["label_mature"]].copy()
    missing = labeled[~labeled["label_mature"]].copy()
    return {
        "purpose": "kd_d5_return_group_feature_research_sidecar",
        "market": "Taiwan stocks",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "signal_start_date": str(labeled["asof_date"].min()) if not labeled.empty else None,
        "signal_end_date": str(labeled["asof_date"].max()) if not labeled.empty else None,
        "horizon_trading_days": horizon_trading_days,
        "target_label": "signal_adjusted_close_to_d5_adjusted_close_return_pct",
        "group_definition": [
            {
                "key": key,
                "label": label,
                "lower": lower if np.isfinite(lower) else None,
                "upper": upper if np.isfinite(upper) else None,
            }
            for key, label, lower, upper, _order in GROUP_DEFINITIONS
        ],
        "ungrouped_definition": "0% <= adjusted D+5 return < 10%",
        "signal_rows": int(len(labeled)),
        "mature_label_rows": int(len(mature)),
        "missing_label_rows": int(len(missing)),
        "grouped_rows": int(len(grouped)),
        "ungrouped_rows": int(len(ungrouped)),
        "unique_grouped_stocks": int(grouped["stock_id"].nunique()) if not grouped.empty else 0,
        "cooldown_grouped_rows": int(len(cooldown)),
        "no_corporate_action_grouped_rows": int(len(no_actions)),
        "corporate_action_event_rows": int(
            mature["corporate_action_event_in_horizon"].fillna(False).astype(bool).sum()
        ),
        "adjusted_price_latest_date": (
            pd.to_datetime(adjusted_prices["date"]).max().date().isoformat()
            if not adjusted_prices.empty
            else None
        ),
        "adjusted_data_asof": (
            str(adjusted_prices["adjusted_data_asof"].dropna().max())
            if not adjusted_prices.empty and adjusted_prices["adjusted_data_asof"].notna().any()
            else None
        ),
        "min_category_count": min_category_count,
        "group_summary": _records(group_summary),
        "top_drivers": {
            str(group_key): _records(group.head(12))
            for group_key, group in top_drivers.groupby("d5_group", sort=False)
        }
        if not top_drivers.empty
        else {},
        "execution_assumption": "No execution simulation; signal close to D+5 close only.",
        "cost_slippage_treatment": "Not applied because this is not a trade-return simulation.",
        "corporate_action_treatment": (
            "Adjusted close labels are primary; factor changes are flagged and no-action sensitivity is exported."
        ),
        "duplicate_signal_treatment": (
            "All fresh events are primary; same-stock non-overlapping 5-day cooldown is exported as sensitivity."
        ),
        "no_lookahead": (
            "KD features are pre-generated as-of observations; D+5 prices are evaluator-only labels."
        ),
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "promotion_decision": "blocked_before_promotion_review",
    }


def load_adjusted_prices(
    events: pd.DataFrame,
    *,
    sqlite_path: Path,
    horizon_trading_days: int,
) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    stock_ids = sorted({str(value).zfill(4) for value in events["stock_id"].dropna()})
    placeholders = ",".join("?" for _ in stock_ids)
    calendar_buffer_days = max(30, horizon_trading_days * 4)
    query = f"""
        select date, stock_id, close, adj_close, adjustment_factor,
               factor_event_count, asof_date as adjusted_data_asof
        from tw_adjusted_ohlcv_daily
        where date >= ?
          and date <= date(?, ?)
          and stock_id in ({placeholders})
        order by stock_id, date
    """
    params = [
        str(events["asof_date"].min())[:10],
        str(events["asof_date"].max())[:10],
        f"+{calendar_buffer_days} day",
        *stock_ids,
    ]
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query, connection, params=params, parse_dates=["date"])


def load_daily_features(events: pd.DataFrame, *, sqlite_path: Path) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=DAILY_FEATURE_COLUMNS)
    stock_ids = sorted({str(value).zfill(4) for value in events["stock_id"].dropna()})
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select {", ".join(DAILY_FEATURE_COLUMNS)}
        from daily_ohlcv_features
        where date between ? and ?
          and stock_id in ({placeholders})
        order by date, stock_id
    """
    params = [
        str(events["asof_date"].min())[:10],
        str(events["asof_date"].max())[:10],
        *stock_ids,
    ]
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query, connection, params=params, parse_dates=["date"])


def write_outputs(
    analysis: dict[str, Any],
    *,
    output_dir: Path,
    args: argparse.Namespace,
) -> None:
    frames = {
        "zhu_walkline_kd_d5_labeled_rows.csv": analysis["labeled_rows"],
        "zhu_walkline_kd_d5_grouped_rows.csv": analysis["grouped_rows"],
        "zhu_walkline_kd_d5_ungrouped_0_10_rows.csv": analysis["ungrouped_rows"],
        "zhu_walkline_kd_d5_cooldown_rows.csv": analysis["cooldown_rows"],
        "zhu_walkline_kd_d5_no_corporate_action_rows.csv": analysis[
            "no_corporate_action_rows"
        ],
        "zhu_walkline_kd_d5_group_summary.csv": analysis["group_summary"],
        "zhu_walkline_kd_d5_numeric_features.csv": analysis["numeric_features"],
        "zhu_walkline_kd_d5_categorical_lift.csv": analysis["categorical_lift"],
        "zhu_walkline_kd_d5_pairwise_numeric.csv": analysis["pairwise_numeric"],
        "zhu_walkline_kd_d5_pairwise_categorical.csv": analysis[
            "pairwise_categorical"
        ],
        "zhu_walkline_kd_d5_top_drivers.csv": analysis["top_drivers"],
        "zhu_walkline_kd_d5_unique_stock_summary.csv": analysis[
            "unique_stock_summary"
        ],
    }
    for name, frame in frames.items():
        _clean_frame(frame).to_csv(output_dir / name, index=False, encoding="utf-8-sig")
    for group_key, _label, _lower, _upper, _order in GROUP_DEFINITIONS:
        group = analysis["grouped_rows"][analysis["grouped_rows"]["d5_group"].eq(group_key)]
        _clean_frame(group).to_csv(
            output_dir / f"zhu_walkline_kd_d5_{group_key.lower()}_stocks.csv",
            index=False,
            encoding="utf-8-sig",
        )
    summary = analysis["summary"]
    (output_dir / "zhu_walkline_kd_d5_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_kd_d5_summary.md").write_text(
        summary_markdown(summary, analysis["group_summary"], analysis["top_drivers"], args=args),
        encoding="utf-8",
    )


def summary_markdown(
    summary: dict[str, Any],
    group_summary: pd.DataFrame,
    top_drivers: pd.DataFrame,
    *,
    args: argparse.Namespace,
) -> str:
    lines = [
        "# Zhu Walkline KD D+5 Group Feature Analysis",
        "",
        "本報告為 shadow evaluator research，不是買進名單或交易指令。",
        "",
        f"- signal window: {summary['signal_start_date']} to {summary['signal_end_date']}",
        f"- horizon: D+{summary['horizon_trading_days']} trading-day adjusted close",
        f"- signal rows: {summary['signal_rows']}",
        f"- mature labels: {summary['mature_label_rows']}",
        f"- grouped rows: {summary['grouped_rows']}",
        f"- ungrouped 0% to <10% rows: {summary['ungrouped_rows']}",
        f"- adjusted price latest date: {summary['adjusted_price_latest_date']}",
        "",
        "## Group Summary",
        "",
        "| scope | group | rows | stocks | avg | median | q25 | q75 | corp action rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in group_summary.iterrows():
        lines.append(
            f"| {row.get('scope', '')} | {row.get('d5_group_label', '')} | "
            f"{row.get('rows', 0)} | {row.get('unique_stocks', 0)} | "
            f"{_format_number(row.get('avg_d5_adjusted_return_pct'))} | "
            f"{_format_number(row.get('median_d5_adjusted_return_pct'))} | "
            f"{_format_number(row.get('q25_d5_adjusted_return_pct'))} | "
            f"{_format_number(row.get('q75_d5_adjusted_return_pct'))} | "
            f"{_format_number(row.get('corporate_action_event_rate'))} |"
        )
    lines.extend(["", "## Top Quantified Drivers", ""])
    if top_drivers.empty:
        lines.append("No stable driver rows at the configured minimum count.")
    else:
        for group_key, group in top_drivers.groupby("d5_group", sort=False):
            label = group["d5_group_label"].iloc[0]
            lines.extend(
                [
                    f"### {label}",
                    "",
                    "| type | driver | count | effect/lift | group | all |",
                    "|---|---|---:|---:|---:|---:|",
                ]
            )
            for _, row in group.head(12).iterrows():
                lines.append(
                    f"| {row.get('driver_type', '')} | {row.get('driver', '')} | "
                    f"{row.get('count', 0)} | {_format_number(row.get('effect_or_lift'))} | "
                    f"{_format_number(row.get('group_value'))} | "
                    f"{_format_number(row.get('all_value'))} |"
                )
            lines.append("")
    lines.extend(
        [
            "## Method Boundary",
            "",
            f"- input: `{args.input_csv}`",
            "- adjusted close is used for grouping; raw close is retained for audit.",
            "- 0% to <10% is intentionally not forced into the three requested groups.",
            "- repeated same-stock signals and corporate-action rows have separate sensitivity scopes.",
            "- no costs or slippage because this is not an execution-return test.",
            "- promotion_decision=blocked_before_promotion_review",
            "- mode=shadow_observation_only",
            "- formal_champion_changed=False",
            "- formal_trade_effect=False",
        ]
    )
    return "\n".join(lines) + "\n"


def _filter_events(events: pd.DataFrame, *, start_date: str, end_date: str) -> pd.DataFrame:
    output = events.copy()
    dates = pd.to_datetime(output["asof_date"], errors="raise")
    output = output[dates.between(pd.Timestamp(start_date), pd.Timestamp(end_date))].copy()
    if "price_row_fresh" in output.columns:
        output = output[output["price_row_fresh"].fillna(False).astype(bool)]
    if "kd_recovery_confirmation" in output.columns:
        output = output[output["kd_recovery_confirmation"].fillna(False).astype(bool)]
    return output.sort_values(["asof_date", "stock_id"]).reset_index(drop=True)


def _add_empty_label_columns(output: pd.DataFrame) -> pd.DataFrame:
    for column in [
        "signal_raw_close",
        "signal_adj_close",
        "signal_adjustment_factor",
        "signal_trade_index",
        "d5_close_date",
        "d5_raw_close",
        "d5_adj_close",
        "d5_adjustment_factor",
        "d5_factor_event_count",
        "d5_adjusted_return_pct",
        "d5_raw_return_pct",
        "raw_adjusted_return_gap_pct",
        "adjusted_data_asof",
    ]:
        output[column] = pd.NA
    output["corporate_action_event_in_horizon"] = False
    output["label_mature"] = False
    return output


def _safe_pct(numerator: Any, denominator: Any) -> pd.Series:
    top = pd.to_numeric(numerator, errors="coerce")
    bottom = pd.to_numeric(denominator, errors="coerce").replace(0.0, np.nan)
    return (top / bottom) * 100.0


def _safe_gap_pct(numerator: Any, denominator: Any) -> pd.Series:
    top = pd.to_numeric(numerator, errors="coerce")
    bottom = pd.to_numeric(denominator, errors="coerce").replace(0.0, np.nan)
    return ((top / bottom) - 1.0) * 100.0


def _to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.select_dtypes(include=["number"]).columns:
        output[column] = output[column].round(6)
    return output


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.map(_clean_output_value)


def _clean_output_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): _json_default(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _json_default(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "item"):
        return _json_default(value.item())
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def _format_number(value: Any) -> str:
    number = _to_float(value)
    return "" if number is None else f"{number:.4f}"


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        default=(
            "reports/zhu_walkline_kd_observations_2026_01_06/"
            "zhu_walkline_range_kd_confirmed_events.csv"
        ),
    )
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--end-date", default="2026-06-30")
    parser.add_argument("--horizon-trading-days", type=int, default=5)
    parser.add_argument("--min-category-count", type=int, default=10)
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_kd_d5_groups_2026_01_06",
    )
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
