"""Analyze Zhu walkline early-observation rows by forward-return bucket.

This script is an evaluator-only research sidecar. It uses future return labels
only after observation rows are generated, and it does not create or modify
orders, positions, holdings, portfolio weights, formal strategy state, or formal
champion state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

RETURN_BUCKETS: list[tuple[str, str, float, float | None, int]] = [
    ("GAIN_21_30", "21%-30%", 20.0, 31.0, 1),
    ("GAIN_31_40", "31%-40%", 31.0, 41.0, 2),
    ("GAIN_41_50", "41%-50%", 41.0, 51.0, 3),
    ("GAIN_GT_50", ">50%", 51.0, None, 4),
]

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
    "forward_return_pct",
    "rise_score",
    "fall_risk_score",
    "rank_by_early_rule",
    "rank_by_rise",
    "vol_ratio_20",
    "sector_rotation_rank",
    "ma20_slope",
    "ma20_slope_pct",
    "close_to_ma20_pct",
    "close_to_ma120_pct",
    "close_to_sma5_pct",
    "close_to_sma10_pct",
    "close_to_sma60_pct",
    "support_gap_pct",
    "invalidation_gap_pct",
    "confirm_gap_pct",
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
    "intraday_return_rankpct",
    "sma20_gap_rankpct",
    "day_volume_ratio_20_rankpct",
    "range_pos_20_rankpct",
    "close_from_high_rankpct",
]

CATEGORICAL_FEATURES = [
    "early_observation_rule",
    "review_bucket",
    "grade",
    "signal_stage",
    "trigger_type",
    "buy_observation_type",
    "buy_trigger_price_role",
    "ma_state",
    "trend_state",
    "kline_state",
    "volume_state",
    "sector",
    "sector_state",
    "market_state",
    "failure_type",
    "sell_warning_type",
]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_csv = REPO_ROOT / args.input_csv
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])

    candidates = pd.read_csv(input_csv, dtype={"stock_id": str})
    daily_features = _load_daily_features_for_candidates(candidates, sqlite_path=sqlite_path)
    analysis = build_forward_return_bucket_analysis(
        candidates,
        daily_features=daily_features,
        min_category_count=args.min_category_count,
    )
    _write_outputs(analysis, output_dir=output_dir, args=args)
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"bucketed_rows_csv={output_dir / 'zhu_walkline_forward_return_bucket_rows.csv'}")
    print(f"bucket_summary_csv={output_dir / 'zhu_walkline_forward_return_bucket_summary.csv'}")
    print(f"numeric_features_csv={output_dir / 'zhu_walkline_forward_return_numeric_features.csv'}")
    print(f"category_lift_csv={output_dir / 'zhu_walkline_forward_return_category_lift.csv'}")
    print(f"reason_drivers_csv={output_dir / 'zhu_walkline_forward_return_reason_drivers.csv'}")
    print(f"summary_json={output_dir / 'zhu_walkline_forward_return_bucket_summary.json'}")
    print(f"summary_md={output_dir / 'zhu_walkline_forward_return_bucket_summary.md'}")
    return 0


def build_forward_return_bucket_analysis(
    candidates: pd.DataFrame,
    *,
    daily_features: pd.DataFrame,
    min_category_count: int = 8,
) -> dict[str, Any]:
    rows = attach_return_buckets(candidates, daily_features=daily_features)
    bucketed = rows[rows["return_bucket"].ne("")].copy()
    bucket_summary = compute_bucket_summary(bucketed)
    numeric_features = compute_numeric_feature_stats(bucketed)
    category_lift = compute_categorical_lift(bucketed, min_count=min_category_count)
    reason_drivers = compute_reason_drivers(
        numeric_features=numeric_features,
        category_lift=category_lift,
        min_count=min_category_count,
    )
    summary = _summary_payload(
        rows=rows,
        bucketed=bucketed,
        bucket_summary=bucket_summary,
        reason_drivers=reason_drivers,
        min_category_count=min_category_count,
    )
    return {
        "bucketed_rows": bucketed,
        "unbucketed_rows": rows[rows["return_bucket"].eq("")].copy(),
        "bucket_summary": bucket_summary,
        "numeric_features": numeric_features,
        "category_lift": category_lift,
        "reason_drivers": reason_drivers,
        "summary": summary,
    }


def attach_return_buckets(candidates: pd.DataFrame, *, daily_features: pd.DataFrame) -> pd.DataFrame:
    frame = candidates.copy()
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    frame["asof_date"] = pd.to_datetime(frame["asof_date"]).dt.strftime("%Y-%m-%d")
    for column in [
        "close",
        "forward_close",
        "forward_return_pct",
        "rise_score",
        "fall_risk_score",
        "rank_by_early_rule",
        "rank_by_rise",
        "vol_ratio_20",
        "sector_rotation_rank",
        "ma20",
        "ma20_slope",
        "ma120",
        "confirm_price",
        "invalidation_price",
        "support_zone_1_label",
        "resistance_zone_1_label",
    ]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    bucket_info = frame["forward_return_pct"].map(assign_forward_return_bucket)
    frame["return_bucket"] = bucket_info.map(lambda item: item[0])
    frame["return_bucket_label"] = bucket_info.map(lambda item: item[1])
    frame["return_bucket_order"] = bucket_info.map(lambda item: item[2])

    if not daily_features.empty:
        features = daily_features.copy()
        features["stock_id"] = features["stock_id"].astype(str).str.zfill(4)
        features["asof_date"] = pd.to_datetime(features["date"]).dt.strftime("%Y-%m-%d")
        features = features.drop(columns=["date"])
        duplicate_columns = [column for column in features.columns if column in frame.columns]
        features = features.rename(columns={column: f"daily_{column}" for column in duplicate_columns})
        features = features.rename(columns={"daily_asof_date": "asof_date", "daily_stock_id": "stock_id"})
        frame = frame.merge(features, on=["asof_date", "stock_id"], how="left")

    close = pd.to_numeric(frame.get("close"), errors="coerce")
    frame["ma20_slope_pct"] = _safe_pct(frame.get("ma20_slope"), frame.get("ma20"))
    frame["close_to_ma20_pct"] = _safe_gap_pct(close, frame.get("ma20"))
    frame["close_to_ma120_pct"] = _safe_gap_pct(close, frame.get("ma120"))
    frame["close_to_sma5_pct"] = _safe_gap_pct(close, frame.get("sma5"))
    frame["close_to_sma10_pct"] = _safe_gap_pct(close, frame.get("sma10"))
    frame["close_to_sma60_pct"] = _safe_gap_pct(close, frame.get("sma60"))
    frame["support_gap_pct"] = _safe_gap_pct(close, frame.get("support_zone_1_label"))
    frame["invalidation_gap_pct"] = _safe_gap_pct(close, frame.get("invalidation_price"))
    frame["confirm_gap_pct"] = _safe_gap_pct(frame.get("confirm_price"), close)
    for column in NUMERIC_FEATURES:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def assign_forward_return_bucket(value: Any) -> tuple[str, str, int]:
    number = _to_float(value)
    if number is None:
        return "", "", 0
    for key, label, lower, upper, order in RETURN_BUCKETS:
        if number >= lower and (upper is None or number < upper):
            return key, label, order
    return "", "", 0


def compute_bucket_summary(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(
            columns=[
                "return_bucket",
                "return_bucket_label",
                "rows",
                "unique_stocks",
                "avg_forward_return_pct",
                "median_forward_return_pct",
            ]
        )
    grouped = rows.groupby(["return_bucket_order", "return_bucket", "return_bucket_label"], dropna=False)
    summary = grouped.agg(
        rows=("stock_id", "count"),
        unique_stocks=("stock_id", "nunique"),
        avg_forward_return_pct=("forward_return_pct", "mean"),
        median_forward_return_pct=("forward_return_pct", "median"),
        min_forward_return_pct=("forward_return_pct", "min"),
        max_forward_return_pct=("forward_return_pct", "max"),
        avg_rise_score=("rise_score", "mean"),
        avg_fall_risk_score=("fall_risk_score", "mean"),
        avg_vol_ratio_20=("vol_ratio_20", "mean"),
        avg_ma20_slope=("ma20_slope", "mean"),
        avg_ma20_slope_pct=("ma20_slope_pct", "mean"),
        avg_close_to_ma20_pct=("close_to_ma20_pct", "mean"),
        avg_close_to_ma120_pct=("close_to_ma120_pct", "mean"),
        avg_sector_rotation_rank=("sector_rotation_rank", "mean"),
        avg_day_volume_ratio_20=("day_volume_ratio_20", "mean"),
        attack_volume_share=("volume_state", lambda series: _share(series, "ATTACK_VOLUME")),
        strict_breakout_share=(
            "early_observation_rule",
            lambda series: _share(series, "STRICT_BREAKOUT"),
        ),
        strict_support_turn_share=(
            "early_observation_rule",
            lambda series: _share(series, "STRICT_SUPPORT_TURN"),
        ),
        sector_leading_share=("sector_state", lambda series: _share(series, "SECTOR_LEADING")),
        range_bound_market_share=(
            "market_state",
            lambda series: _share(series, "MARKET_RANGE_BOUND"),
        ),
    )
    summary = summary.reset_index().sort_values("return_bucket_order")
    return _round_numeric(summary)


def compute_numeric_feature_stats(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if rows.empty:
        return pd.DataFrame()
    for feature in NUMERIC_FEATURES:
        if feature not in rows.columns:
            continue
        values = pd.to_numeric(rows[feature], errors="coerce")
        all_mean = values.mean()
        all_median = values.median()
        all_std = values.std(ddof=0)
        bucket_order = pd.to_numeric(rows["return_bucket_order"], errors="coerce")
        if values.nunique(dropna=True) < 2 or bucket_order.nunique(dropna=True) < 2:
            spearman = 0.0
        else:
            spearman = values.rank(method="average").corr(
                bucket_order.rank(method="average"),
                method="pearson",
            )
        for bucket_order, bucket, label, bucket_rows in _iter_bucket_rows(rows):
            bucket_values = pd.to_numeric(bucket_rows[feature], errors="coerce")
            mean = bucket_values.mean()
            records.append(
                {
                    "feature": feature,
                    "return_bucket_order": bucket_order,
                    "return_bucket": bucket,
                    "return_bucket_label": label,
                    "rows": int(bucket_values.notna().sum()),
                    "mean": mean,
                    "median": bucket_values.median(),
                    "all_mean": all_mean,
                    "all_median": all_median,
                    "mean_delta_vs_all": mean - all_mean,
                    "standardized_delta_vs_all": (mean - all_mean) / all_std
                    if all_std and pd.notna(all_std)
                    else 0.0,
                    "spearman_with_bucket_order": spearman,
                }
            )
    return _round_numeric(pd.DataFrame(records))


def compute_categorical_lift(rows: pd.DataFrame, *, min_count: int = 8) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    total = len(rows)
    if total == 0:
        return pd.DataFrame()
    for feature in CATEGORICAL_FEATURES:
        if feature not in rows.columns:
            continue
        feature_values = rows[feature].fillna("").astype(str).str.strip()
        all_counts = feature_values.value_counts(dropna=False)
        for bucket_order, bucket, label, bucket_rows in _iter_bucket_rows(rows):
            bucket_values = bucket_rows[feature].fillna("").astype(str).str.strip()
            bucket_total = len(bucket_values)
            for value, count in bucket_values.value_counts(dropna=False).items():
                if value == "" or int(count) < min_count:
                    continue
                all_count = int(all_counts.get(value, 0))
                all_share = all_count / total if total else 0.0
                bucket_share = int(count) / bucket_total if bucket_total else 0.0
                records.append(
                    {
                        "feature": feature,
                        "value": value,
                        "return_bucket_order": bucket_order,
                        "return_bucket": bucket,
                        "return_bucket_label": label,
                        "count": int(count),
                        "bucket_rows": bucket_total,
                        "all_count": all_count,
                        "bucket_share": bucket_share,
                        "all_share": all_share,
                        "lift": bucket_share / all_share if all_share else 0.0,
                        "avg_forward_return_pct": bucket_rows.loc[
                            bucket_values.eq(value), "forward_return_pct"
                        ].mean(),
                    }
                )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame["reason_family"] = frame["feature"].map(_reason_family)
    frame = frame.sort_values(
        ["return_bucket_order", "lift", "count"],
        ascending=[True, False, False],
    )
    return _round_numeric(frame)


def compute_reason_drivers(
    *,
    numeric_features: pd.DataFrame,
    category_lift: pd.DataFrame,
    min_count: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if not category_lift.empty:
        category = category_lift[
            (category_lift["count"] >= min_count)
            & (category_lift["all_count"] >= min_count)
            & (category_lift["lift"] >= 1.15)
        ].copy()
        category["driver_type"] = "CATEGORY_LIFT"
        category["driver"] = category["feature"] + "=" + category["value"]
        category["driver_score"] = category["lift"] * category["count"].pow(0.5)
        for _, row in category.iterrows():
            records.append(
                {
                    "return_bucket_order": row["return_bucket_order"],
                    "return_bucket": row["return_bucket"],
                    "return_bucket_label": row["return_bucket_label"],
                    "driver_type": row["driver_type"],
                    "reason_family": row["reason_family"],
                    "driver": row["driver"],
                    "count": row["count"],
                    "bucket_share": row["bucket_share"],
                    "all_share": row["all_share"],
                    "lift": row["lift"],
                    "mean": "",
                    "all_mean": "",
                    "standardized_delta_vs_all": "",
                    "driver_score": row["driver_score"],
                }
            )
    if not numeric_features.empty:
        numeric = numeric_features[numeric_features["feature"].ne("forward_return_pct")].copy()
        numeric["abs_delta"] = numeric["standardized_delta_vs_all"].abs()
        numeric = numeric[(numeric["rows"] >= min_count) & (numeric["abs_delta"] >= 0.05)]
        numeric["driver_score"] = numeric["abs_delta"] * numeric["rows"].pow(0.5)
        for _, row in numeric.iterrows():
            direction = "HIGH" if row["standardized_delta_vs_all"] > 0 else "LOW"
            records.append(
                {
                    "return_bucket_order": row["return_bucket_order"],
                    "return_bucket": row["return_bucket"],
                    "return_bucket_label": row["return_bucket_label"],
                    "driver_type": "NUMERIC_EFFECT",
                    "reason_family": _numeric_reason_family(str(row["feature"])),
                    "driver": f"{direction}_{row['feature']}",
                    "count": row["rows"],
                    "bucket_share": "",
                    "all_share": "",
                    "lift": "",
                    "mean": row["mean"],
                    "all_mean": row["all_mean"],
                    "standardized_delta_vs_all": row["standardized_delta_vs_all"],
                    "driver_score": row["driver_score"],
                }
            )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame = frame.sort_values(
        ["return_bucket_order", "driver_score"],
        ascending=[True, False],
    )
    return _round_numeric(frame)


def _load_daily_features_for_candidates(candidates: pd.DataFrame, *, sqlite_path: Path) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=DAILY_FEATURE_COLUMNS)
    start_date = str(candidates["asof_date"].min())[:10]
    end_date = str(candidates["asof_date"].max())[:10]
    stock_ids = sorted({str(value).zfill(4) for value in candidates["stock_id"].dropna().unique()})
    if not stock_ids:
        return pd.DataFrame(columns=DAILY_FEATURE_COLUMNS)
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select {", ".join(DAILY_FEATURE_COLUMNS)}
        from daily_ohlcv_features
        where date between ? and ?
          and stock_id in ({placeholders})
        order by date, stock_id
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, end_date, *stock_ids],
            parse_dates=["date"],
        )


def _write_outputs(analysis: dict[str, Any], *, output_dir: Path, args: argparse.Namespace) -> None:
    bucketed_rows = _clean_frame(analysis["bucketed_rows"])
    unbucketed_rows = _clean_frame(analysis["unbucketed_rows"])
    bucket_summary = _clean_frame(analysis["bucket_summary"])
    numeric_features = _clean_frame(analysis["numeric_features"])
    category_lift = _clean_frame(analysis["category_lift"])
    reason_drivers = _clean_frame(analysis["reason_drivers"])
    summary = analysis["summary"]

    bucketed_rows.to_csv(
        output_dir / "zhu_walkline_forward_return_bucket_rows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    unbucketed_rows.to_csv(
        output_dir / "zhu_walkline_forward_return_unbucketed_rows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    bucket_summary.to_csv(
        output_dir / "zhu_walkline_forward_return_bucket_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    numeric_features.to_csv(
        output_dir / "zhu_walkline_forward_return_numeric_features.csv",
        index=False,
        encoding="utf-8-sig",
    )
    category_lift.to_csv(
        output_dir / "zhu_walkline_forward_return_category_lift.csv",
        index=False,
        encoding="utf-8-sig",
    )
    reason_drivers.to_csv(
        output_dir / "zhu_walkline_forward_return_reason_drivers.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (output_dir / "zhu_walkline_forward_return_bucket_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_forward_return_bucket_summary.md").write_text(
        _summary_markdown(summary, bucket_summary, reason_drivers, args=args),
        encoding="utf-8",
    )


def _summary_payload(
    *,
    rows: pd.DataFrame,
    bucketed: pd.DataFrame,
    bucket_summary: pd.DataFrame,
    reason_drivers: pd.DataFrame,
    min_category_count: int,
) -> dict[str, Any]:
    bucket_counts = (
        bucketed["return_bucket"].value_counts().sort_index().to_dict()
        if not bucketed.empty
        else {}
    )
    top_drivers: dict[str, list[dict[str, Any]]] = {}
    if not reason_drivers.empty:
        for bucket, group in reason_drivers.groupby("return_bucket", sort=False):
            top_drivers[str(bucket)] = _records_for_json(group.head(12))
    return {
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "purpose": "forward_return_bucket_research_sidecar",
        "target_label": "20_trading_day_forward_close_return_pct",
        "bucket_definition": [
            {
                "bucket": key,
                "label": label,
                "lower_inclusive_pct": lower,
                "upper_exclusive_pct": upper,
            }
            for key, label, lower, upper, _ in RETURN_BUCKETS
        ],
        "input_rows": int(len(rows)),
        "bucketed_rows": int(len(bucketed)),
        "unbucketed_rows": int(len(rows) - len(bucketed)),
        "unique_stocks": int(bucketed["stock_id"].nunique()) if not bucketed.empty else 0,
        "date_count": int(bucketed["asof_date"].nunique()) if not bucketed.empty else 0,
        "min_category_count": int(min_category_count),
        "bucket_counts": {str(key): int(value) for key, value in bucket_counts.items()},
        "bucket_summary": _records_for_json(bucket_summary),
        "top_reason_drivers": top_drivers,
        "forward_returns_are_evaluator_only": True,
        "no_formal_strategy_modified": True,
        "no_formal_champion_modified": True,
        "no_formal_trade_effect": True,
    }


def _summary_markdown(
    summary: dict[str, Any],
    bucket_summary: pd.DataFrame,
    reason_drivers: pd.DataFrame,
    *,
    args: argparse.Namespace,
) -> str:
    lines = [
        "# Zhu Walkline Forward Return Bucket Research",
        "",
        "本輸出是 shadow observation / evaluator-only 研究 sidecar，不是買進名單，不是交易指令。",
        "20 個交易日後報酬只用於事後分桶與特徵歸因，不可回灌為當日選股條件。",
        "",
        f"- input_csv: `{args.input_csv}`",
        f"- input rows: {summary['input_rows']}",
        f"- bucketed rows: {summary['bucketed_rows']}",
        f"- unbucketed rows: {summary['unbucketed_rows']}",
        f"- unique stocks: {summary['unique_stocks']}",
        f"- date count: {summary['date_count']}",
        "",
        "## Bucket Summary",
        "",
        _markdown_table(
            bucket_summary,
            [
                "return_bucket_label",
                "rows",
                "unique_stocks",
                "avg_forward_return_pct",
                "median_forward_return_pct",
                "avg_rise_score",
                "avg_fall_risk_score",
                "avg_vol_ratio_20",
                "avg_ma20_slope_pct",
                "avg_close_to_ma120_pct",
                "strict_breakout_share",
                "attack_volume_share",
                "sector_leading_share",
            ],
        ),
        "",
        "## Top Quantified Drivers",
        "",
        _markdown_table(
            reason_drivers.head(40),
            [
                "return_bucket_label",
                "driver_type",
                "reason_family",
                "driver",
                "count",
                "lift",
                "standardized_delta_vs_all",
                "driver_score",
            ],
        ),
        "",
        "## Boundary",
        "",
        "- mode=shadow_observation_only",
        "- formal_champion_changed=False",
        "- formal_trade_effect=False",
        "- no formal strategy modified",
        "- no formal champion modified",
        "- no formal trade effect",
    ]
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        default=(
            "reports/zhu_walkline_early_observation_labels_2026_01_06_fwd20p/"
            "zhu_walkline_early_observation_candidates.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_forward_return_bucket_research_2026_01_06",
    )
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--min-category-count", type=int, default=8)
    return parser.parse_args(argv)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


def _iter_bucket_rows(rows: pd.DataFrame) -> list[tuple[int, str, str, pd.DataFrame]]:
    groups: list[tuple[int, str, str, pd.DataFrame]] = []
    for (order, bucket, label), group in rows.groupby(
        ["return_bucket_order", "return_bucket", "return_bucket_label"],
        dropna=False,
        sort=True,
    ):
        groups.append((int(order), str(bucket), str(label), group))
    return groups


def _safe_gap_pct(numerator: Any, denominator: Any) -> pd.Series:
    numerator_series = pd.to_numeric(numerator, errors="coerce")
    denominator_series = pd.to_numeric(denominator, errors="coerce")
    return ((numerator_series / denominator_series) - 1.0) * 100.0


def _safe_pct(numerator: Any, denominator: Any) -> pd.Series:
    numerator_series = pd.to_numeric(numerator, errors="coerce")
    denominator_series = pd.to_numeric(denominator, errors="coerce")
    return (numerator_series / denominator_series) * 100.0


def _share(series: pd.Series, value: str) -> float:
    clean = series.fillna("").astype(str)
    return float(clean.eq(value).mean()) if len(clean) else 0.0


def _reason_family(feature: str) -> str:
    if feature == "sector":
        return "SECTOR_THEME"
    if feature in {"early_observation_rule", "trigger_type", "buy_observation_type", "signal_stage"}:
        return "WALKLINE_SIGNAL"
    if feature in {"ma_state", "trend_state"}:
        return "TREND_MA_STRUCTURE"
    if feature in {"volume_state", "kline_state"}:
        return "KLINE_VOLUME"
    if feature in {"sector_state", "market_state"}:
        return "MARKET_SECTOR_CONTEXT"
    if feature in {"failure_type", "sell_warning_type", "review_bucket"}:
        return "RISK_WARNING"
    return "OTHER"


def _numeric_reason_family(feature: str) -> str:
    if "volume" in feature or "vol_" in feature:
        return "VOLUME"
    if "ma" in feature or "sma" in feature:
        return "TREND_MA_STRUCTURE"
    if "sector" in feature:
        return "MARKET_SECTOR_CONTEXT"
    if "risk" in feature or "invalidation" in feature or "support" in feature:
        return "RISK_SUPPORT"
    if "range" in feature or "close_location" in feature or "gap" in feature:
        return "PRICE_POSITION"
    return "NUMERIC"


def _round_numeric(frame: pd.DataFrame, decimals: int = 6) -> pd.DataFrame:
    output = frame.copy()
    numeric_columns = output.select_dtypes(include=["number"]).columns
    output[numeric_columns] = output[numeric_columns].round(decimals)
    return output


def _records_for_json(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): _json_default(value) for key, value in row.items()}
        for row in _clean_frame(frame).to_dict("records")
    ]


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    selected = frame[[column for column in columns if column in frame.columns]].copy()
    if selected.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(selected.columns) + " |",
        "| " + " | ".join("---" for _ in selected.columns) + " |",
    ]
    for _, row in selected.iterrows():
        lines.append("| " + " | ".join(str(_clean_value(row[column])) for column in selected.columns) + " |")
    return "\n".join(lines)


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    return output.where(pd.notna(output), "")


def _clean_value(value: Any) -> Any:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is None:
        return None
    if pd.isna(value):
        return None
    return value


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
