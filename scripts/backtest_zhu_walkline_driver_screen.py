"""Run a shadow driver-screen overlay and rolling backtest for Zhu walkline rows.

The screen uses only as-of features inspired by the forward-return bucket
research. Forward returns are attached only for evaluator metrics after the
screen is formed. This script does not create or modify orders, positions,
holdings, portfolio weights, formal strategy state, or formal champion state.
"""

from __future__ import annotations

import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.export_zhu_walkline_early_observation_candidates import (  # noqa: E402
    _load_forward_price_rows,
    attach_forward_return_labels,
)
from abc_quant.data.yahoo_concepts import (  # noqa: E402
    load_important_yahoo_concept_snapshot,
)
from abc_quant.features.yahoo_concept_rotation import (  # noqa: E402
    apply_hierarchical_context_gate,
    attach_best_yahoo_concept_context,
    compute_yahoo_concept_rotation,
    write_yahoo_concept_rotation,
)


DAILY_JOIN_COLUMNS = [
    "date",
    "stock_id",
    "open_to_close_pct",
    "gap_up_pct",
    "close_location_in_bar",
    "sma5",
    "sma10",
    "sma20",
    "sma60",
    "day_volume_ratio_20",
    "intraday_return_rankpct",
    "range_pos_20_rankpct",
    "close_from_high_rankpct",
]

SCREEN_OUTPUT_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "close",
    "forward_close_date",
    "forward_close",
    "forward_return_pct",
    "driver_score",
    "driver_reasons",
    "early_observation_rule",
    "sector",
    "sector_state",
    "market_state",
    "market_gate_pass",
    "volume_state",
    "kline_state",
    "signal_stage",
    "fall_risk_score",
    "rise_score",
    "vol_ratio_20",
    "open_to_close_pct",
    "close_location_in_bar",
    "close_to_sma5_pct",
    "sector_gate_pass",
    "concept_memberships",
    "best_concept_name",
    "concept_state",
    "concept_strength_score",
    "concept_above_sma20_ratio",
    "concept_sma20_slope_positive_ratio",
    "concept_positive_return_5d_ratio",
    "concept_median_return_5d_pct",
    "concept_membership_mode",
    "concept_snapshot_id",
    "concept_snapshot_date",
    "concept_gate_pass",
    "context_alignment_pass",
    "individual_score_gate_pass",
    "hierarchy_gate_order",
    "hierarchy_gate_stage",
    "hierarchy_observation_pass",
    "context_failure_reason",
    "stop_reference",
]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])
    candidates = pd.read_csv(REPO_ROOT / args.candidates_csv, dtype={"stock_id": str})
    daily_features = _load_daily_features_for_candidates(candidates, sqlite_path=sqlite_path)
    price_rows = _load_forward_price_rows(
        sqlite_path,
        start_date=str(candidates["asof_date"].min()),
        end_date=str(candidates["asof_date"].max()),
        horizon_trading_days=args.horizon_trading_days,
    )
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    hierarchy_gate = args.hierarchy_gate or str(
        config.get("concept_context", {}).get("hierarchy_gate_default", "required")
    )
    if hierarchy_gate not in {"required", "diagnostic", "off"}:
        raise ValueError(f"unsupported hierarchy gate mode: {hierarchy_gate}")
    allow_static_backfill = args.allow_static_current_backfill
    if allow_static_backfill is None:
        allow_static_backfill = bool(
            config.get("concept_context", {}).get("allow_static_current_backfill", False)
        )
    concept_manifest: dict[str, Any] = {}
    concept_membership = pd.DataFrame()
    concept_rotation = pd.DataFrame()
    if hierarchy_gate != "off":
        concept_sqlite_path = Path(config["data"]["yahoo_concept_sqlite_path"])
        concept_manifest, concept_membership = load_important_yahoo_concept_snapshot(
            concept_sqlite_path,
            snapshot_id=args.concept_snapshot_id,
        )
        concept_membership["snapshot_date"] = str(concept_manifest["snapshot_date"])
        rotation_end_date = max(
            str(candidates["asof_date"].max())[:10],
            str(concept_manifest["snapshot_date"]),
        )
        concept_price_features = _load_concept_price_features(
            candidates,
            membership=concept_membership,
            sqlite_path=sqlite_path,
            end_date=rotation_end_date,
        )
        concept_rotation = compute_yahoo_concept_rotation(
            concept_price_features,
            concept_membership,
            snapshot_date=str(concept_manifest["snapshot_date"]),
            allow_static_current_backfill=bool(allow_static_backfill),
            min_available_members=int(
                config.get("concept_context", {}).get("min_available_members", 3)
            ),
            date_from=str(candidates["asof_date"].min())[:10],
            date_to=rotation_end_date,
        )
        write_yahoo_concept_rotation(concept_rotation, sqlite_path=concept_sqlite_path)

    result = run_driver_screen_backtest(
        candidates,
        daily_features=daily_features,
        price_rows=price_rows,
        min_driver_score=args.min_driver_score,
        horizon_trading_days=args.horizon_trading_days,
        rolling_window_days=args.rolling_window_days,
        concept_membership=concept_membership,
        concept_rotation=concept_rotation,
        concept_snapshot_date=str(concept_manifest.get("snapshot_date", "")),
        concept_snapshot_manifest=concept_manifest,
        hierarchy_gate=hierarchy_gate,
    )
    _write_outputs(result, output_dir=output_dir, args=args)
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"screened_rows_csv={output_dir / 'zhu_walkline_driver_screen_rows.csv'}")
    print(f"daily_metrics_csv={output_dir / 'zhu_walkline_driver_screen_daily_metrics.csv'}")
    print(f"monthly_metrics_csv={output_dir / 'zhu_walkline_driver_screen_monthly_metrics.csv'}")
    print(f"rolling_metrics_csv={output_dir / 'zhu_walkline_driver_screen_rolling_metrics.csv'}")
    print(f"summary_json={output_dir / 'zhu_walkline_driver_screen_summary.json'}")
    print(f"summary_md={output_dir / 'zhu_walkline_driver_screen_summary.md'}")
    return 0


def run_driver_screen_backtest(
    candidates: pd.DataFrame,
    *,
    daily_features: pd.DataFrame,
    price_rows: pd.DataFrame,
    min_driver_score: int = 11,
    horizon_trading_days: int = 20,
    rolling_window_days: int = 20,
    concept_membership: pd.DataFrame | None = None,
    concept_rotation: pd.DataFrame | None = None,
    concept_snapshot_date: str = "",
    concept_snapshot_manifest: dict[str, Any] | None = None,
    hierarchy_gate: str = "off",
) -> dict[str, Any]:
    labeled = attach_forward_return_labels(
        candidates,
        price_rows=price_rows,
        horizon_trading_days=horizon_trading_days,
    )
    scored = score_driver_screen(labeled, daily_features=daily_features)
    if hierarchy_gate != "off":
        scored = attach_best_yahoo_concept_context(
            scored,
            membership=concept_membership if concept_membership is not None else pd.DataFrame(),
            rotation=concept_rotation if concept_rotation is not None else pd.DataFrame(),
            snapshot_date=concept_snapshot_date,
        )
        scored = apply_hierarchical_context_gate(
            scored,
            min_driver_score=min_driver_score,
        )
    driver_score_only = scored[scored["driver_score"] >= float(min_driver_score)].copy()
    selected = driver_score_only.copy()
    if hierarchy_gate == "required":
        selected = selected[selected["hierarchy_observation_pass"]].copy()
    selected_mature = selected[
        pd.to_numeric(selected["forward_return_pct"], errors="coerce").notna()
    ].copy()
    valid_scored = scored[pd.to_numeric(scored["forward_return_pct"], errors="coerce").notna()].copy()
    mature_driver_score_only = driver_score_only[
        pd.to_numeric(driver_score_only["forward_return_pct"], errors="coerce").notna()
    ].copy()
    baselines = build_same_count_baselines(selected_mature, valid_scored)
    driver_controls = build_same_count_driver_controls(
        selected_mature,
        mature_driver_score_only,
    )
    all_frames = {
        "driver_screen": selected_mature,
        "driver_score_only": mature_driver_score_only,
        "all_candidates": valid_scored,
        **baselines,
        **driver_controls,
    }
    summary = build_summary_payload(
        frames=all_frames,
        min_driver_score=min_driver_score,
        horizon_trading_days=horizon_trading_days,
        rolling_window_days=rolling_window_days,
        hierarchy_gate=hierarchy_gate,
        selected_observation_rows=len(selected),
        scored_rows=scored,
        concept_snapshot_manifest=concept_snapshot_manifest or {},
    )
    return {
        "scored_rows": scored,
        "screened_rows": selected,
        "driver_score_only_rows": driver_score_only,
        "baseline_top_rise": baselines["same_count_top_rise"],
        "baseline_random": baselines["same_count_random"],
        "driver_control_top": driver_controls["same_count_driver_score"],
        "driver_control_random": driver_controls["same_count_driver_random"],
        "daily_metrics": compute_period_metrics(all_frames, period="asof_date"),
        "monthly_metrics": compute_period_metrics(all_frames, period="month"),
        "rolling_metrics": compute_rolling_window_metrics(
            all_frames,
            rolling_window_days=rolling_window_days,
        ),
        "summary": summary,
    }


def score_driver_screen(candidates: pd.DataFrame, *, daily_features: pd.DataFrame) -> pd.DataFrame:
    frame = candidates.copy()
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    frame["asof_date"] = pd.to_datetime(frame["asof_date"]).dt.strftime("%Y-%m-%d")
    frame = _attach_daily_features(frame, daily_features)
    for column in [
        "forward_return_pct",
        "close",
        "rise_score",
        "fall_risk_score",
        "vol_ratio_20",
        "open_to_close_pct",
        "close_location_in_bar",
        "sma5",
        "day_volume_ratio_20",
    ]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["close_to_sma5_pct"] = ((frame["close"] / frame["sma5"]) - 1.0) * 100.0
    rules = _driver_rule_masks(frame)
    frame["driver_score"] = 0.0
    reason_columns: list[str] = []
    for name, points, mask in rules:
        column = f"driver_{name}"
        frame[column] = mask.fillna(False).astype(bool)
        reason_columns.append(column)
        frame.loc[frame[column], "driver_score"] += points
    frame["driver_reasons"] = frame[reason_columns].apply(
        lambda row: "|".join(
            column.replace("driver_", "")
            for column, enabled in row.items()
            if bool(enabled)
        ),
        axis=1,
    )
    return frame


def _driver_rule_masks(frame: pd.DataFrame) -> list[tuple[str, int, pd.Series]]:
    return [
        ("sector_electronic_components", 3, frame["sector"].eq("電子零組件")),
        ("supporting_sector", 1, frame["sector"].isin(["光電", "其他電子"])),
        ("strict_breakout", 2, frame["early_observation_rule"].eq("STRICT_BREAKOUT")),
        (
            "attack_volume",
            2,
            frame["volume_state"].eq("ATTACK_VOLUME")
            | (pd.to_numeric(frame["vol_ratio_20"], errors="coerce") >= 1.8)
            | (pd.to_numeric(frame["day_volume_ratio_20"], errors="coerce") >= 1.8),
        ),
        ("attack_red_k", 1, frame["kline_state"].eq("ATTACK_RED_K")),
        (
            "strong_intraday_close",
            1,
            (pd.to_numeric(frame["open_to_close_pct"], errors="coerce") >= 0.04)
            & (pd.to_numeric(frame["close_location_in_bar"], errors="coerce") >= 0.8),
        ),
        (
            "short_ma_gap",
            1,
            (((pd.to_numeric(frame["close"], errors="coerce") / pd.to_numeric(frame["sma5"], errors="coerce")) - 1.0) * 100.0)
            >= 7.0,
        ),
        ("sector_leading", 1, frame["sector_state"].eq("SECTOR_LEADING")),
        (
            "confirmed_low_risk",
            1,
            frame["signal_stage"].eq("CONFIRMED")
            & (pd.to_numeric(frame["fall_risk_score"], errors="coerce") <= 3.0),
        ),
        (
            "clean_review",
            1,
            frame["sell_warning_type"].fillna("").astype(str).eq("")
            & frame["failure_type"].fillna("").astype(str).eq("")
            & frame["review_bucket"].fillna("").astype(str).eq("CLEAN_REVIEW"),
        ),
    ]


def build_same_count_baselines(
    selected: pd.DataFrame,
    universe: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    if selected.empty:
        empty = pd.DataFrame(columns=universe.columns)
        return {"same_count_top_rise": empty, "same_count_random": empty}
    top_frames: list[pd.DataFrame] = []
    random_frames: list[pd.DataFrame] = []
    counts = selected.groupby("asof_date").size().to_dict()
    for asof_date, count in counts.items():
        day = universe[universe["asof_date"].eq(asof_date)].copy()
        if day.empty:
            continue
        top_frames.append(
            day.sort_values(
                ["rise_score", "fall_risk_score", "stock_id"],
                ascending=[False, True, True],
            ).head(int(count))
        )
        day["_stable_random_key"] = day["stock_id"].map(lambda stock_id: _stable_hash(f"{asof_date}-{stock_id}"))
        random_frames.append(day.sort_values("_stable_random_key").head(int(count)).drop(columns=["_stable_random_key"]))
    return {
        "same_count_top_rise": pd.concat(top_frames, ignore_index=True) if top_frames else pd.DataFrame(columns=universe.columns),
        "same_count_random": pd.concat(random_frames, ignore_index=True) if random_frames else pd.DataFrame(columns=universe.columns),
    }


def build_same_count_driver_controls(
    selected: pd.DataFrame,
    driver_universe: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build fair same-date controls from rows that already pass driver_score."""

    if selected.empty:
        empty = pd.DataFrame(columns=driver_universe.columns)
        return {"same_count_driver_score": empty, "same_count_driver_random": empty}
    top_frames: list[pd.DataFrame] = []
    random_frames: list[pd.DataFrame] = []
    counts = selected.groupby("asof_date").size().to_dict()
    for asof_date, count in counts.items():
        day = driver_universe[driver_universe["asof_date"].eq(asof_date)].copy()
        if day.empty:
            continue
        top_frames.append(
            day.sort_values(
                ["driver_score", "rise_score", "fall_risk_score", "stock_id"],
                ascending=[False, False, True, True],
            ).head(int(count))
        )
        day["_stable_random_key"] = day["stock_id"].map(
            lambda stock_id: _stable_hash(f"driver-{asof_date}-{stock_id}")
        )
        random_frames.append(
            day.sort_values("_stable_random_key")
            .head(int(count))
            .drop(columns=["_stable_random_key"])
        )
    return {
        "same_count_driver_score": (
            pd.concat(top_frames, ignore_index=True)
            if top_frames
            else pd.DataFrame(columns=driver_universe.columns)
        ),
        "same_count_driver_random": (
            pd.concat(random_frames, ignore_index=True)
            if random_frames
            else pd.DataFrame(columns=driver_universe.columns)
        ),
    }


def compute_period_metrics(frames: dict[str, pd.DataFrame], *, period: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for cohort, frame in frames.items():
        if frame.empty:
            continue
        data = frame.copy()
        data["month"] = data["asof_date"].astype(str).str.slice(0, 7)
        for period_value, group in data.groupby(period, dropna=False):
            records.append({"cohort": cohort, period: period_value, **_metrics(group)})
    return _round_numeric(pd.DataFrame(records))


def compute_rolling_window_metrics(
    frames: dict[str, pd.DataFrame],
    *,
    rolling_window_days: int,
) -> pd.DataFrame:
    empty_columns = [
        "cohort",
        "window_start_date",
        "window_end_date",
        "window_trading_days",
        *_metrics(pd.DataFrame()).keys(),
    ]
    all_dates = sorted(
        {
            str(date)
            for frame in frames.values()
            if not frame.empty
            for date in frame["asof_date"].dropna().unique()
        }
    )
    records: list[dict[str, Any]] = []
    if rolling_window_days <= 0 or len(all_dates) < rolling_window_days:
        return pd.DataFrame(columns=empty_columns)
    for end_index in range(rolling_window_days - 1, len(all_dates)):
        window_dates = set(all_dates[end_index - rolling_window_days + 1 : end_index + 1])
        for cohort, frame in frames.items():
            if frame.empty:
                continue
            window = frame[frame["asof_date"].isin(window_dates)]
            records.append(
                {
                    "cohort": cohort,
                    "window_start_date": min(window_dates),
                    "window_end_date": max(window_dates),
                    "window_trading_days": rolling_window_days,
                    **_metrics(window),
                }
            )
    if not records:
        return pd.DataFrame(columns=empty_columns)
    return _round_numeric(pd.DataFrame(records))


def build_summary_payload(
    *,
    frames: dict[str, pd.DataFrame],
    min_driver_score: int,
    horizon_trading_days: int,
    rolling_window_days: int,
    hierarchy_gate: str,
    selected_observation_rows: int,
    scored_rows: pd.DataFrame,
    concept_snapshot_manifest: dict[str, Any],
) -> dict[str, Any]:
    summary_rows = []
    for cohort, frame in frames.items():
        row = {"cohort": cohort, **_metrics(frame)}
        summary_rows.append(row)
    summary_frame = _round_numeric(pd.DataFrame(summary_rows))
    driver = _cohort_row(summary_frame, "driver_screen")
    top_rise = _cohort_row(summary_frame, "same_count_top_rise")
    random = _cohort_row(summary_frame, "same_count_random")
    driver_control = _cohort_row(summary_frame, "same_count_driver_score")
    driver_random_control = _cohort_row(summary_frame, "same_count_driver_random")
    hierarchy_stage_counts: list[dict[str, Any]] = []
    if "hierarchy_gate_stage" in scored_rows.columns:
        hierarchy_stage_counts = [
            {"hierarchy_gate_stage": str(stage), "rows": int(count)}
            for stage, count in scored_rows["hierarchy_gate_stage"].value_counts().items()
        ]
    concept_snapshot = {
        key: concept_snapshot_manifest.get(key)
        for key in [
            "snapshot_id",
            "snapshot_date",
            "fetched_at",
            "category_count",
            "membership_count",
            "unique_stock_count",
            "content_sha256",
            "importance",
            "is_important",
        ]
        if key in concept_snapshot_manifest
    }
    if "concept_membership_mode" in scored_rows.columns:
        modes = sorted(
            {
                str(value)
                for value in scored_rows["concept_membership_mode"].dropna().unique()
                if str(value)
            }
        )
        concept_snapshot["backtest_membership_mode"] = "|".join(modes)
    return {
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "purpose": "driver_screen_rolling_backtest_sidecar",
        "min_driver_score": int(min_driver_score),
        "horizon_trading_days": int(horizon_trading_days),
        "rolling_window_days": int(rolling_window_days),
        "hierarchy_gate": hierarchy_gate,
        "selected_observation_rows": int(selected_observation_rows),
        "hierarchy_stage_counts": hierarchy_stage_counts,
        "concept_snapshot": concept_snapshot,
        "screen_rules": _screen_rules_payload(),
        "cohort_summary": _records_for_json(summary_frame),
        "driver_minus_same_count_top_rise": _metric_delta(driver, top_rise),
        "driver_minus_same_count_random": _metric_delta(driver, random),
        "driver_minus_same_count_driver_score": _metric_delta(driver, driver_control),
        "driver_minus_same_count_driver_random": _metric_delta(
            driver, driver_random_control
        ),
        "forward_returns_are_evaluator_only": True,
        "no_formal_strategy_modified": True,
        "no_formal_champion_modified": True,
        "no_formal_trade_effect": True,
    }


def _metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "unique_stocks": 0,
            "date_count": 0,
            "avg_forward_return_pct": None,
            "median_forward_return_pct": None,
            "hit_rate_20pct": None,
            "hit_rate_50pct": None,
            "downside_rate_lt_0": None,
            "tail_loss_rate_le_neg10": None,
            "avg_driver_score": None,
        }
    returns = pd.to_numeric(frame["forward_return_pct"], errors="coerce")
    valid = frame[returns.notna()].copy()
    returns = pd.to_numeric(valid["forward_return_pct"], errors="coerce")
    return {
        "rows": int(len(valid)),
        "unique_stocks": int(valid["stock_id"].nunique()) if "stock_id" in valid else 0,
        "date_count": int(valid["asof_date"].nunique()) if "asof_date" in valid else 0,
        "avg_forward_return_pct": returns.mean(),
        "median_forward_return_pct": returns.median(),
        "hit_rate_20pct": (returns >= 20.0).mean(),
        "hit_rate_50pct": (returns >= 50.0).mean(),
        "downside_rate_lt_0": (returns < 0.0).mean(),
        "tail_loss_rate_le_neg10": (returns <= -10.0).mean(),
        "avg_driver_score": pd.to_numeric(valid.get("driver_score"), errors="coerce").mean(),
    }


def _load_daily_features_for_candidates(candidates: pd.DataFrame, *, sqlite_path: Path) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=DAILY_JOIN_COLUMNS)
    start_date = str(candidates["asof_date"].min())[:10]
    end_date = str(candidates["asof_date"].max())[:10]
    stock_ids = sorted({str(value).zfill(4) for value in candidates["stock_id"].dropna().unique()})
    if not stock_ids:
        return pd.DataFrame(columns=DAILY_JOIN_COLUMNS)
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select {", ".join(DAILY_JOIN_COLUMNS)}
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


def _load_concept_price_features(
    candidates: pd.DataFrame,
    *,
    membership: pd.DataFrame,
    sqlite_path: Path,
    end_date: str | None = None,
) -> pd.DataFrame:
    if candidates.empty or membership.empty:
        return pd.DataFrame(columns=["date", "stock_id", "close", "sma20"])
    start = pd.Timestamp(str(candidates["asof_date"].min())[:10]) - timedelta(days=45)
    end = pd.Timestamp(end_date or str(candidates["asof_date"].max())[:10])
    with sqlite3.connect(sqlite_path) as connection:
        prices = pd.read_sql_query(
            """
            select date, stock_id, close, sma20
            from daily_ohlcv_features
            where date between ? and ?
            order by stock_id, date
            """,
            connection,
            params=[start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")],
            parse_dates=["date"],
            dtype={"stock_id": str},
        )
    member_ids = set(membership["stock_id"].astype(str).str.zfill(4))
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    return prices[prices["stock_id"].isin(member_ids)].copy()


def _attach_daily_features(frame: pd.DataFrame, daily_features: pd.DataFrame) -> pd.DataFrame:
    if daily_features.empty:
        for column in DAILY_JOIN_COLUMNS:
            if column not in {"date", "stock_id"} and column not in frame.columns:
                frame[column] = pd.NA
        return frame
    daily = daily_features.copy()
    daily["stock_id"] = daily["stock_id"].astype(str).str.zfill(4)
    daily["asof_date"] = pd.to_datetime(daily["date"]).dt.strftime("%Y-%m-%d")
    daily = daily.drop(columns=["date"])
    duplicate_columns = [column for column in daily.columns if column in frame.columns and column not in {"asof_date", "stock_id"}]
    daily = daily.rename(columns={column: f"daily_{column}" for column in duplicate_columns})
    merged = frame.merge(daily, on=["asof_date", "stock_id"], how="left")
    for column in duplicate_columns:
        merged[column] = merged.get(column).combine_first(merged.get(f"daily_{column}"))
        merged = merged.drop(columns=[f"daily_{column}"])
    return merged


def _write_outputs(result: dict[str, Any], *, output_dir: Path, args: argparse.Namespace) -> None:
    screened = _screen_output_frame(result["screened_rows"])
    driver_score_only = _screen_output_frame(result["driver_score_only_rows"])
    scored = _clean_frame(result["scored_rows"])
    top_rise = _screen_output_frame(result["baseline_top_rise"])
    random = _screen_output_frame(result["baseline_random"])
    driver_control_top = _screen_output_frame(result["driver_control_top"])
    driver_control_random = _screen_output_frame(result["driver_control_random"])
    daily = _clean_frame(result["daily_metrics"])
    monthly = _clean_frame(result["monthly_metrics"])
    rolling = _clean_frame(result["rolling_metrics"])
    summary = result["summary"]
    screened.to_csv(output_dir / "zhu_walkline_driver_screen_rows.csv", index=False, encoding="utf-8-sig")
    driver_score_only.to_csv(
        output_dir / "zhu_walkline_driver_score_only_rows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    scored.to_csv(output_dir / "zhu_walkline_driver_screen_scored_universe.csv", index=False, encoding="utf-8-sig")
    top_rise.to_csv(output_dir / "zhu_walkline_driver_screen_same_count_top_rise.csv", index=False, encoding="utf-8-sig")
    random.to_csv(output_dir / "zhu_walkline_driver_screen_same_count_random.csv", index=False, encoding="utf-8-sig")
    driver_control_top.to_csv(
        output_dir / "zhu_walkline_same_count_driver_score.csv",
        index=False,
        encoding="utf-8-sig",
    )
    driver_control_random.to_csv(
        output_dir / "zhu_walkline_same_count_driver_random.csv",
        index=False,
        encoding="utf-8-sig",
    )
    daily.to_csv(output_dir / "zhu_walkline_driver_screen_daily_metrics.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(output_dir / "zhu_walkline_driver_screen_monthly_metrics.csv", index=False, encoding="utf-8-sig")
    rolling.to_csv(output_dir / "zhu_walkline_driver_screen_rolling_metrics.csv", index=False, encoding="utf-8-sig")
    (output_dir / "zhu_walkline_driver_screen_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_driver_screen_summary.md").write_text(
        _summary_markdown(summary, monthly, rolling, args=args),
        encoding="utf-8",
    )


def _screen_output_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in SCREEN_OUTPUT_COLUMNS:
        if column not in output.columns:
            output[column] = ""
    return _clean_frame(output[SCREEN_OUTPUT_COLUMNS])


def _summary_markdown(summary: dict[str, Any], monthly: pd.DataFrame, rolling: pd.DataFrame, *, args: argparse.Namespace) -> str:
    cohort_summary = pd.DataFrame(summary["cohort_summary"])
    lines = [
        "# Zhu Walkline Driver Screen Rolling Backtest",
        "",
        "本輸出是 shadow observation / evaluator-only 研究 sidecar，不是買進名單，不是交易指令。",
        "Driver screen 只用 as-of 特徵；forward return 僅用於事後評估。",
        "",
        f"- candidates_csv: `{args.candidates_csv}`",
        f"- min_driver_score: {summary['min_driver_score']}",
        f"- horizon trading days: {summary['horizon_trading_days']}",
        f"- rolling window days: {summary['rolling_window_days']}",
        f"- hierarchy gate: {summary['hierarchy_gate']}",
        f"- selected observation rows (mature + immature): {summary['selected_observation_rows']}",
        f"- Yahoo concept snapshot: `{summary.get('concept_snapshot', {}).get('snapshot_id', '')}`",
        f"- concept membership mode: `{summary.get('concept_snapshot', {}).get('backtest_membership_mode', '')}`",
        "",
        "## Hierarchy Gate",
        "",
        "固定順序：大盤 -> 類股 -> 概念股 -> 個股 driver_score。前一層未通過，後一層不構成候選。",
        "Yahoo 重要快照倒灌僅屬使用者授權的 shadow 實驗，不冒充歷史 point-in-time 成分。",
        "",
        _markdown_table(
            pd.DataFrame(summary.get("hierarchy_stage_counts", [])),
            ["hierarchy_gate_stage", "rows"],
        ),
        "",
        "## Cohort Summary",
        "",
        _markdown_table(
            cohort_summary,
            [
                "cohort",
                "rows",
                "unique_stocks",
                "date_count",
                "avg_forward_return_pct",
                "median_forward_return_pct",
                "hit_rate_20pct",
                "hit_rate_50pct",
                "downside_rate_lt_0",
                "tail_loss_rate_le_neg10",
                "avg_driver_score",
            ],
        ),
        "",
        "## Monthly Metrics",
        "",
        _markdown_table(
            monthly[
                monthly["cohort"].isin(
                    [
                        "driver_screen",
                        "driver_score_only",
                        "same_count_driver_score",
                        "same_count_driver_random",
                        "same_count_top_rise",
                        "same_count_random",
                    ]
                )
            ],
            [
                "cohort",
                "month",
                "rows",
                "avg_forward_return_pct",
                "median_forward_return_pct",
                "hit_rate_20pct",
                "hit_rate_50pct",
                "downside_rate_lt_0",
            ],
        ),
        "",
        "## Latest Rolling Window",
        "",
        _markdown_table(
            rolling.sort_values("window_end_date").groupby("cohort", as_index=False).tail(1),
            [
                "cohort",
                "window_start_date",
                "window_end_date",
                "rows",
                "avg_forward_return_pct",
                "hit_rate_20pct",
                "hit_rate_50pct",
                "downside_rate_lt_0",
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


def _screen_rules_payload() -> list[dict[str, Any]]:
    return [
        {
            "rule": "hierarchy_gate_order",
            "points": 0,
            "condition": "market -> sector -> Yahoo concept breadth -> individual driver_score",
        },
        {"rule": "sector_electronic_components", "points": 3, "condition": "sector == 電子零組件"},
        {"rule": "supporting_sector", "points": 1, "condition": "sector in 光電,其他電子"},
        {"rule": "strict_breakout", "points": 2, "condition": "early_observation_rule == STRICT_BREAKOUT"},
        {"rule": "attack_volume", "points": 2, "condition": "volume_state == ATTACK_VOLUME or vol_ratio_20/day_volume_ratio_20 >= 1.8"},
        {"rule": "attack_red_k", "points": 1, "condition": "kline_state == ATTACK_RED_K"},
        {"rule": "strong_intraday_close", "points": 1, "condition": "open_to_close_pct >= 4% and close_location_in_bar >= 0.8"},
        {"rule": "short_ma_gap", "points": 1, "condition": "close_to_sma5_pct >= 7%"},
        {"rule": "sector_leading", "points": 1, "condition": "sector_state == SECTOR_LEADING"},
        {"rule": "confirmed_low_risk", "points": 1, "condition": "signal_stage == CONFIRMED and fall_risk_score <= 3"},
        {"rule": "clean_review", "points": 1, "condition": "no sell/failure warning and review_bucket == CLEAN_REVIEW"},
    ]


def _metric_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "avg_forward_return_pct",
        "median_forward_return_pct",
        "hit_rate_20pct",
        "hit_rate_50pct",
        "downside_rate_lt_0",
        "tail_loss_rate_le_neg10",
    ]
    return {
        field: _to_float(left.get(field)) - _to_float(right.get(field))
        if _to_float(left.get(field)) is not None and _to_float(right.get(field)) is not None
        else None
        for field in fields
    }


def _cohort_row(summary: pd.DataFrame, cohort: str) -> dict[str, Any]:
    row = summary[summary["cohort"].eq(cohort)]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates-csv",
        default=(
            "reports/zhu_walkline_early_observation_labels_2026_01_06/"
            "zhu_walkline_early_observation_candidates.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_driver_screen_backtest_2026_01_06",
    )
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--min-driver-score", type=int, default=11)
    parser.add_argument("--horizon-trading-days", type=int, default=20)
    parser.add_argument("--rolling-window-days", type=int, default=20)
    parser.add_argument(
        "--hierarchy-gate",
        choices=["required", "diagnostic", "off"],
        default=None,
    )
    parser.add_argument("--concept-snapshot-id")
    parser.add_argument(
        "--allow-static-current-backfill",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    return parser.parse_args(argv)


def _stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    selected = frame[[column for column in columns if column in frame.columns]].copy()
    lines = [
        "| " + " | ".join(selected.columns) + " |",
        "| " + " | ".join("---" for _ in selected.columns) + " |",
    ]
    for _, row in selected.iterrows():
        lines.append("| " + " | ".join(str(_clean_value(row[column])) for column in selected.columns) + " |")
    return "\n".join(lines)


def _round_numeric(frame: pd.DataFrame, decimals: int = 6) -> pd.DataFrame:
    output = frame.copy()
    numeric_columns = output.select_dtypes(include=["number"]).columns
    output[numeric_columns] = output[numeric_columns].round(decimals)
    return output


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.copy().where(pd.notna(frame), "")


def _clean_value(value: Any) -> Any:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return value


def _records_for_json(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): _json_default(value) for key, value in row.items()}
        for row in _clean_frame(frame).to_dict("records")
    ]


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
