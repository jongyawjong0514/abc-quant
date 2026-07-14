"""Replay one frozen Zhu early-start rule over the full PIT Taiwan universe."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gc
import json
from pathlib import Path
import sqlite3
import sys
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from abc_quant.features.pre_signal_features import (  # noqa: E402
    build_pre_signal_feature_frame,
)
from abc_quant.features.shadow_strength import apply_shadow_strength_score  # noqa: E402
from abc_quant.features.walkline_features import (  # noqa: E402
    compute_walkline_feature_history,
)
from scripts.analyze_zhu_walkline_kd_d5_groups import attach_d5_labels  # noqa: E402
from scripts.analyze_zhu_walkline_kd_d5_pre_signal_features import (  # noqa: E402
    assert_no_lookahead,
    load_local_histories,
    load_wide_panel,
)
from scripts.optimize_zhu_walkline_early_start_parameters import (  # noqa: E402
    apply_same_stock_cooldown,
)
from scripts.score_zhu_walkline_daily_shadow_strength import (  # noqa: E402
    load_frozen_rules,
)


FOUR_COMPONENT_EXPORT_COLUMNS = [
    "asof_date",
    "stock_id",
    "pre_price_source_date",
    "pre_main_force_source_date",
    "pre_margin_available_date",
    "pre_main_force_net_lots_1d",
    "pre5_upper_tail_count",
    "pre_day_volume_ratio_20",
    "pre_margin_balance_change_5d_pct",
    "shadow_strength_main_force_pass",
    "shadow_strength_no_upper_tail_pass",
    "shadow_strength_volume_ratio_pass",
    "shadow_strength_margin_change_pass",
    "shadow_strength_main_force_points",
    "shadow_strength_no_upper_tail_points",
    "shadow_strength_volume_ratio_points",
    "shadow_strength_margin_change_points",
    "shadow_strength_available_components",
    "shadow_strength_passed_components",
    "shadow_strength_complete",
    "shadow_strength_score",
    "shadow_strength_tier",
    "shadow_strength_score_status",
    "shadow_strength_missing_components",
    "shadow_strength_passed_component_names",
    "shadow_strength_feature_available_date",
    "shadow_strength_rank_within_signal_date",
    "shadow_strength_rank_pct_within_signal_date",
    "shadow_strength_rankable_count",
    "shadow_strength_score_version",
    "shadow_strength_mode",
    "shadow_strength_formal_trade_effect",
]


@dataclass(frozen=True)
class FixedFullMarketRule:
    """The single rule frozen before this full-market replay."""

    max_k: float
    min_k_change_1d: float
    min_daily_return_pct: float
    max_volume_ratio_20: float
    max_close_to_sma20_pct: float
    max_distance_from_trailing_5d_low_pct: float


def run_replay(
    *,
    config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Execute the fixed-rule replay and archive auditable artifacts."""
    started = perf_counter()
    analysis = config["analysis"]
    guards = config["universe_guards"]
    sqlite_path = Path(config["data"]["sqlite_path"])
    rule = FixedFullMarketRule(**config["fixed_rule"])
    timings: dict[str, float] = {}

    step = perf_counter()
    prices = load_raw_price_history(
        sqlite_path,
        start_date=analysis["history_start"],
        end_date=analysis["signal_end"],
    )
    timings["load_raw_prices_seconds"] = perf_counter() - step

    step = perf_counter()
    daily = build_full_market_feature_rows(
        prices,
        signal_start=analysis["signal_start"],
        signal_end=analysis["signal_end"],
    )
    timings["build_feature_history_seconds"] = perf_counter() - step
    del prices
    gc.collect()

    step = perf_counter()
    pit = load_pit_universe(
        sqlite_path,
        start_date=analysis["signal_start"],
        end_date=analysis["signal_end"],
        markets=[str(value) for value in guards["markets"]],
    )
    universe, pit_audit = merge_pit_universe(daily, pit)
    timings["join_pit_universe_seconds"] = perf_counter() - step
    del pit
    gc.collect()

    universe["universe_guard_pass"] = (
        pd.to_numeric(universe["history_rows"], errors="coerce").ge(
            int(guards["minimum_history_rows"])
        )
        & pd.to_numeric(universe["avg_turnover_20_twd"], errors="coerce").ge(
            float(guards["minimum_avg_turnover_20_twd"])
        )
    )
    eligible = universe[universe["universe_guard_pass"]].copy()
    eligible["fixed_rule_pass"] = fixed_early_start_mask(eligible, rule)
    pre_cooldown = eligible[eligible["fixed_rule_pass"]].copy()
    pre_cooldown["asof_date"] = pd.to_datetime(
        pre_cooldown["date"], errors="raise"
    )
    cooldown = apply_same_stock_cooldown(
        pre_cooldown,
        minimum_trade_days=int(guards["same_stock_cooldown_trade_days"]),
    )
    candidates = cooldown[cooldown["same_stock_cooldown"]].copy()
    candidates["asof_date"] = candidates["asof_date"].dt.strftime("%Y-%m-%d")
    candidates = candidates.sort_values(["asof_date", "stock_id"]).reset_index(
        drop=True
    )

    evaluation = eligible[
        [
            "date",
            "stock_id",
            "stock_name",
            "market",
            "close",
            "signal_trade_index",
        ]
    ].copy()
    evaluation = evaluation.rename(columns={"date": "asof_date"})
    evaluation["asof_date"] = pd.to_datetime(
        evaluation["asof_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    candidate_keys = set(
        candidates[["asof_date", "stock_id"]].astype(str).agg("|".join, axis=1)
    )
    evaluation_keys = evaluation[["asof_date", "stock_id"]].astype(str).agg(
        "|".join, axis=1
    )
    evaluation["early_start_candidate"] = evaluation_keys.isin(candidate_keys)

    step = perf_counter()
    adjusted = load_adjusted_price_history(
        sqlite_path,
        start_date=analysis["signal_start"],
        end_date=analysis["signal_end"],
        horizon_trading_days=int(analysis["label_horizon_trading_days"]),
    )
    labeled = attach_d5_labels(
        evaluation,
        adjusted_prices=adjusted,
        horizon_trading_days=int(analysis["label_horizon_trading_days"]),
    )
    timings["attach_adjusted_d5_labels_seconds"] = perf_counter() - step
    del adjusted, evaluation
    gc.collect()

    label_mature = _as_bool(labeled["label_mature"])
    corporate_action = _as_bool(labeled["corporate_action_event_in_horizon"])
    primary = labeled[label_mature & ~corporate_action].copy()
    mature_all = labeled[label_mature].copy()
    primary_metric = evaluate_full_market_screen(
        primary,
        scope="mature_no_forward_corporate_action",
        target_return_pct=float(analysis["target_return_pct"]),
        large_gain_return_pct=float(analysis["large_gain_return_pct"]),
    )
    robustness_metric = evaluate_full_market_screen(
        mature_all,
        scope="mature_including_corporate_actions",
        target_return_pct=float(analysis["target_return_pct"]),
        large_gain_return_pct=float(analysis["large_gain_return_pct"]),
    )
    monthly = build_monthly_metrics(
        primary,
        target_return_pct=float(analysis["target_return_pct"]),
        large_gain_return_pct=float(analysis["large_gain_return_pct"]),
    )

    label_columns = [
        "asof_date",
        "stock_id",
        "adjusted_data_asof",
        "signal_raw_close",
        "signal_adj_close",
        "signal_adjustment_factor",
        "d5_close_date",
        "d5_raw_close",
        "d5_adj_close",
        "d5_adjustment_factor",
        "d5_adjusted_return_pct",
        "d5_raw_return_pct",
        "raw_adjusted_return_gap_pct",
        "corporate_action_event_in_horizon",
        "label_mature",
    ]
    candidate_rows = candidates.merge(
        labeled[label_columns],
        on=["asof_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    candidate_rows["primary_evaluation_eligible"] = (
        _as_bool(candidate_rows["label_mature"])
        & ~_as_bool(candidate_rows["corporate_action_event_in_horizon"])
    )

    step = perf_counter()
    confirmed_path = _repo_path(config["future_kd_linkage"]["confirmed_events_csv"])
    confirmed = pd.read_csv(confirmed_path, dtype={"stock_id": str})
    candidate_rows = link_future_kd_confirmations(
        candidate_rows,
        confirmed_events=confirmed,
        daily_features=daily,
        minimum_lead_days=int(
            config["future_kd_linkage"]["minimum_lead_trade_days"]
        ),
        maximum_lead_days=int(
            config["future_kd_linkage"]["maximum_lead_trade_days"]
        ),
    )
    timings["future_kd_linkage_seconds"] = perf_counter() - step

    step = perf_counter()
    strength = score_candidate_four_components(
        candidate_rows,
        sqlite_path=sqlite_path,
        finlab_root=Path(config["data"]["finlab_items_root"]),
        rules_csv=_repo_path(config["data"]["shadow_strength_rules_csv"]),
    )
    candidate_rows = candidate_rows.merge(
        strength,
        on=["asof_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    timings["four_component_scoring_seconds"] = perf_counter() - step

    daily_metrics = build_daily_metrics(primary)
    strength_buckets = build_four_component_bucket_metrics(candidate_rows)
    strength_gain10_monotonic = _nondecreasing(
        strength_buckets["d5_gain_ge10_rate"]
    )
    linkage_metric = summarize_future_kd_linkage(candidate_rows)
    edge_checks = evaluate_retrospective_edge_gate(
        primary_metric,
        monthly=monthly,
        config=config["retrospective_edge_gate"],
    )
    retrospective_edge_observed = all(edge_checks.values())

    source_audit = {
        **database_source_audit(sqlite_path),
        **pit_audit,
        "raw_feature_rows_in_signal_window": int(len(daily)),
        "eligible_universe_rows": int(len(eligible)),
        "pre_cooldown_candidate_rows": int(len(pre_cooldown)),
        "post_cooldown_candidate_rows": int(len(candidate_rows)),
        "candidate_unique_stocks": int(candidate_rows["stock_id"].nunique()),
        "candidate_signal_days": int(candidate_rows["asof_date"].nunique()),
        "complete_four_component_rows": int(
            candidate_rows["shadow_strength_complete"]
            .fillna(False)
            .astype(bool)
            .sum()
        ),
        "four_component_forbidden_raw_margin_balance_exported": False,
        "four_component_forbidden_foreign_shares_exported": False,
    }
    timings["total_seconds"] = perf_counter() - started
    summary = {
        "purpose": "fixed_rule_full_market_point_in_time_early_start_replay",
        "market": "TW",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "signal_start": analysis["signal_start"],
        "signal_end": analysis["signal_end"],
        "fixed_rule": asdict(rule),
        "universe_guards": guards,
        "primary_metric": primary_metric,
        "generated_candidate_rows": int(len(candidate_rows)),
        "robustness_metric": robustness_metric,
        "future_kd_linkage": linkage_metric,
        "four_component_bucket_gain10_monotonic": strength_gain10_monotonic,
        "retrospective_edge_checks": edge_checks,
        "retrospective_edge_observed": retrospective_edge_observed,
        "source_audit": source_audit,
        "timings_seconds": timings,
        "selection_features": [
            "kd_k9",
            "kd_k_change_1d",
            "daily_return_pct",
            "day_volume_ratio_20",
            "close_to_sma20_pct",
            "distance_from_trailing_5d_low_pct",
        ],
        "label_boundary": (
            "raw OHLCV supplies selection features; current adjusted OHLCV is used only "
            "for evaluator D+5 labels; forward corporate actions are excluded only from "
            "primary evaluation, never from candidate selection"
        ),
        "four_component_role": (
            "main force, no upper tail, volume ratio, and margin change are scored after "
            "selection for shadow reporting only; they do not enter the fixed mask"
        ),
        "selection_period_previously_inspected": bool(
            config["governance"]["selection_period_previously_inspected"]
        ),
        "research_scope": config["governance"]["research_scope"],
        "live_deployable": bool(config["governance"]["live_deployable"]),
        "next_required_gate": config["governance"]["next_required_gate"],
        "promotion_decision": config["governance"]["promotion_decision"],
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
    }
    result = {
        "candidate_rows": candidate_rows,
        "monthly_metrics": monthly,
        "daily_metrics": daily_metrics,
        "strength_buckets": strength_buckets,
        "summary": summary,
    }
    write_outputs(result, output_dir=output_dir)
    return result


def load_raw_price_history(
    sqlite_path: Path,
    *,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    query = """
        select date, stock_id, open, high, low, close, volume
        from daily_ohlcv_features
        where date between ? and ?
          and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, end_date],
            parse_dates=["date"],
        )


def load_pit_universe(
    sqlite_path: Path,
    *,
    start_date: str,
    end_date: str,
    markets: list[str],
) -> pd.DataFrame:
    placeholders = ",".join("?" for _ in markets)
    query = f"""
        select date, stock_id, stock_name, market, effective_source_date,
               listing_date, pit_quality_rank
        from stock_pit_sector_membership_daily
        where date between ? and ?
          and market in ({placeholders})
        order by date, stock_id, pit_quality_rank
    """
    with sqlite3.connect(sqlite_path) as connection:
        frame = pd.read_sql_query(
            query,
            connection,
            params=[start_date, end_date, *markets],
            parse_dates=["date", "effective_source_date", "listing_date"],
        )
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    return frame.sort_values(["date", "stock_id", "pit_quality_rank"]).drop_duplicates(
        ["date", "stock_id"], keep="first"
    )


def build_full_market_feature_rows(
    prices: pd.DataFrame,
    *,
    signal_start: str,
    signal_end: str,
) -> pd.DataFrame:
    history = compute_walkline_feature_history(prices, asof_date=signal_end)
    grouped = history.groupby("stock_id", group_keys=False, sort=False)
    history["signal_trade_index"] = grouped.cumcount().astype(int)
    history["history_rows"] = history["signal_trade_index"] + 1
    history["kd_k_change_1d"] = grouped["kd_k9"].diff()
    history["daily_return_pct"] = pd.to_numeric(
        history["return_1d"], errors="coerce"
    ) * 100.0
    history["close_to_sma20_pct"] = (
        pd.to_numeric(history["close"], errors="coerce")
        / pd.to_numeric(history["ma20"], errors="coerce")
        - 1.0
    ) * 100.0
    history["distance_from_trailing_5d_low_pct"] = (
        pd.to_numeric(history["close"], errors="coerce")
        / pd.to_numeric(history["swing_low_1"], errors="coerce")
        - 1.0
    ) * 100.0
    history["day_volume_ratio_20"] = pd.to_numeric(
        history["vol_ratio_20"], errors="coerce"
    )
    history["avg_turnover_20_twd"] = pd.to_numeric(
        history["amount_ma20"], errors="coerce"
    )
    dates = pd.to_datetime(history["date"], errors="raise")
    columns = [
        "date",
        "stock_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "signal_trade_index",
        "history_rows",
        "kd_k9",
        "kd_d9",
        "kd_k_change_1d",
        "daily_return_pct",
        "day_volume_ratio_20",
        "close_to_sma20_pct",
        "distance_from_trailing_5d_low_pct",
        "avg_turnover_20_twd",
    ]
    return history.loc[
        dates.between(pd.Timestamp(signal_start), pd.Timestamp(signal_end)), columns
    ].reset_index(drop=True)


def merge_pit_universe(
    daily_features: pd.DataFrame,
    pit_universe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if daily_features.duplicated(["date", "stock_id"]).any():
        raise ValueError("daily feature keys are not unique")
    if pit_universe.duplicated(["date", "stock_id"]).any():
        raise ValueError("PIT universe keys are not unique")
    effective = pd.to_datetime(pit_universe["effective_source_date"], errors="coerce")
    listing = pd.to_datetime(pit_universe["listing_date"], errors="coerce")
    date = pd.to_datetime(pit_universe["date"], errors="raise")
    effective_violations = int((effective.notna() & effective.gt(date)).sum())
    listing_violations = int((listing.notna() & listing.gt(date)).sum())
    if effective_violations or listing_violations:
        raise ValueError(
            "PIT universe date violation: "
            f"effective={effective_violations}, listing={listing_violations}"
        )
    merged = daily_features.merge(
        pit_universe,
        on=["date", "stock_id"],
        how="inner",
        validate="one_to_one",
    )
    return merged, {
        "daily_feature_rows": int(len(daily_features)),
        "pit_universe_rows": int(len(pit_universe)),
        "pit_matched_rows": int(len(merged)),
        "pit_unmatched_daily_feature_rows": int(len(daily_features) - len(merged)),
        "pit_effective_source_date_violations": effective_violations,
        "pit_listing_date_violations": listing_violations,
    }


def fixed_early_start_mask(
    rows: pd.DataFrame,
    rule: FixedFullMarketRule,
) -> pd.Series:
    """Apply the frozen mask without reading outcomes or future KD fields."""
    required = {
        "kd_k9",
        "kd_k_change_1d",
        "daily_return_pct",
        "day_volume_ratio_20",
        "close_to_sma20_pct",
        "distance_from_trailing_5d_low_pct",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"full-market rows missing rule columns: {sorted(missing)}")
    mask = pd.to_numeric(rows["kd_k9"], errors="coerce").le(rule.max_k)
    mask &= pd.to_numeric(rows["kd_k_change_1d"], errors="coerce").ge(
        rule.min_k_change_1d
    )
    mask &= pd.to_numeric(rows["daily_return_pct"], errors="coerce").ge(
        rule.min_daily_return_pct
    )
    mask &= pd.to_numeric(rows["day_volume_ratio_20"], errors="coerce").le(
        rule.max_volume_ratio_20
    )
    mask &= pd.to_numeric(rows["close_to_sma20_pct"], errors="coerce").le(
        rule.max_close_to_sma20_pct
    )
    mask &= pd.to_numeric(
        rows["distance_from_trailing_5d_low_pct"], errors="coerce"
    ).le(rule.max_distance_from_trailing_5d_low_pct)
    return mask.fillna(False)


def load_adjusted_price_history(
    sqlite_path: Path,
    *,
    start_date: str,
    end_date: str,
    horizon_trading_days: int,
) -> pd.DataFrame:
    calendar_buffer_days = max(30, horizon_trading_days * 4)
    query = """
        select date, stock_id, close, adj_close, adjustment_factor,
               factor_event_count, asof_date as adjusted_data_asof
        from tw_adjusted_ohlcv_daily
        where date >= ?
          and date <= date(?, ?)
          and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, end_date, f"+{calendar_buffer_days} day"],
            parse_dates=["date"],
        )


def evaluate_full_market_screen(
    rows: pd.DataFrame,
    *,
    scope: str,
    target_return_pct: float,
    large_gain_return_pct: float,
) -> dict[str, Any]:
    predicted = _as_bool(rows["early_start_candidate"])
    returns = pd.to_numeric(rows["d5_adjusted_return_pct"], errors="coerce")
    actual = returns.ge(target_return_pct)
    selected = rows[predicted].copy()
    selected_returns = returns[predicted]
    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())
    tn = int((~predicted & ~actual).sum())
    precision = _divide(tp, tp + fp)
    recall = _divide(tp, tp + fn)
    specificity = _divide(tn, tn + fp)
    base_rate = float(actual.mean()) if len(rows) else 0.0
    total_days = int(pd.to_datetime(rows["asof_date"]).nunique())
    selected_days = int(pd.to_datetime(selected["asof_date"]).nunique())
    return {
        "scope": scope,
        "universe_rows": int(len(rows)),
        "candidate_rows": int(predicted.sum()),
        "candidate_unique_stocks": int(selected["stock_id"].nunique()),
        "total_signal_days": total_days,
        "candidate_signal_days": selected_days,
        "empty_candidate_days": total_days - selected_days,
        "coverage": _divide(int(predicted.sum()), len(rows)),
        "base_gain_ge10_rate": base_rate,
        "precision_gain_ge10": precision,
        "precision_lift_vs_all": _divide(precision, base_rate),
        "recall_gain_ge10": recall,
        "specificity_gain_ge10": specificity,
        "balanced_accuracy_gain_ge10": (recall + specificity) / 2.0,
        "gain_ge20_rate": float(selected_returns.ge(large_gain_return_pct).mean())
        if len(selected_returns)
        else 0.0,
        "loss_rate": float(selected_returns.lt(0).mean())
        if len(selected_returns)
        else 0.0,
        "avg_d5_adjusted_return_pct": float(selected_returns.mean())
        if len(selected_returns)
        else 0.0,
        "median_d5_adjusted_return_pct": float(selected_returns.median())
        if len(selected_returns)
        else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def build_monthly_metrics(
    rows: pd.DataFrame,
    *,
    target_return_pct: float,
    large_gain_return_pct: float,
) -> pd.DataFrame:
    frame = rows.copy()
    frame["month"] = pd.to_datetime(frame["asof_date"]).dt.to_period("M").astype(str)
    records: list[dict[str, Any]] = []
    for month, group in frame.groupby("month", sort=True):
        records.append(
            {
                "month": month,
                **evaluate_full_market_screen(
                    group,
                    scope="mature_no_forward_corporate_action",
                    target_return_pct=target_return_pct,
                    large_gain_return_pct=large_gain_return_pct,
                ),
            }
        )
    return pd.DataFrame(records)


def build_daily_metrics(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    frame["asof_date"] = pd.to_datetime(frame["asof_date"]).dt.strftime("%Y-%m-%d")
    records: list[dict[str, Any]] = []
    for date, group in frame.groupby("asof_date", sort=True):
        predicted = _as_bool(group["early_start_candidate"])
        returns = pd.to_numeric(group.loc[predicted, "d5_adjusted_return_pct"], errors="coerce")
        records.append(
            {
                "asof_date": date,
                "eligible_rows": int(len(group)),
                "candidate_rows": int(predicted.sum()),
                "candidate_gain_ge10_rate": float(returns.ge(10).mean())
                if len(returns)
                else np.nan,
                "candidate_loss_rate": float(returns.lt(0).mean())
                if len(returns)
                else np.nan,
            }
        )
    return pd.DataFrame(records)


def link_future_kd_confirmations(
    candidates: pd.DataFrame,
    *,
    confirmed_events: pd.DataFrame,
    daily_features: pd.DataFrame,
    minimum_lead_days: int,
    maximum_lead_days: int,
) -> pd.DataFrame:
    """Add evaluator-only linkage to the next formal KD confirmation."""
    output = candidates.copy().reset_index(drop=True)
    output["future_kd_confirmation_within_window"] = False
    output["future_kd_linkage_mature"] = False
    output["future_kd_signal_date"] = ""
    output["future_kd_lead_trade_days"] = np.nan
    output["candidate_to_future_kd_return_pct"] = np.nan
    if output.empty or confirmed_events.empty:
        return output

    index_rows = daily_features[
        ["date", "stock_id", "signal_trade_index", "close"]
    ].copy()
    index_rows["date"] = pd.to_datetime(index_rows["date"], errors="raise")
    index_rows["stock_id"] = index_rows["stock_id"].astype(str).str.zfill(4)
    maximum_index = index_rows.groupby("stock_id")["signal_trade_index"].max()
    confirmed = confirmed_events.copy()
    confirmed["date"] = pd.to_datetime(confirmed["asof_date"], errors="raise")
    confirmed["stock_id"] = confirmed["stock_id"].astype(str).str.zfill(4)
    confirmed = confirmed.merge(
        index_rows,
        on=["date", "stock_id"],
        how="inner",
        validate="many_to_one",
    )
    confirmed_groups = {
        stock_id: group.sort_values("signal_trade_index")
        for stock_id, group in confirmed.groupby("stock_id", sort=False)
    }
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["asof_date"] = pd.to_datetime(output["asof_date"], errors="raise")
    for index, row in output.iterrows():
        last_index = pd.to_numeric(
            pd.Series([maximum_index.get(str(row["stock_id"]))]), errors="coerce"
        ).iloc[0]
        if pd.notna(last_index):
            output.at[index, "future_kd_linkage_mature"] = (
                float(last_index) - float(row["signal_trade_index"])
                >= maximum_lead_days
            )
        future = confirmed_groups.get(str(row["stock_id"]))
        if future is None:
            continue
        lead = pd.to_numeric(future["signal_trade_index"], errors="coerce") - float(
            row["signal_trade_index"]
        )
        matches = future[lead.between(minimum_lead_days, maximum_lead_days)].copy()
        if matches.empty:
            continue
        matches["_lead"] = lead.loc[matches.index]
        match = matches.sort_values(["_lead", "date"]).iloc[0]
        output.at[index, "future_kd_confirmation_within_window"] = True
        output.at[index, "future_kd_signal_date"] = pd.Timestamp(match["date"]).strftime(
            "%Y-%m-%d"
        )
        output.at[index, "future_kd_lead_trade_days"] = float(match["_lead"])
        candidate_close = float(row["close"])
        future_close = float(match["close_y"] if "close_y" in match else match["close"])
        output.at[index, "candidate_to_future_kd_return_pct"] = (
            future_close / candidate_close - 1.0
        ) * 100.0
    output["asof_date"] = output["asof_date"].dt.strftime("%Y-%m-%d")
    return output


def score_candidate_four_components(
    candidates: pd.DataFrame,
    *,
    sqlite_path: Path,
    finlab_root: Path,
    rules_csv: Path,
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=FOUR_COMPONENT_EXPORT_COLUMNS)
    keys = candidates[["asof_date", "stock_id"]].copy()
    stock_ids = sorted(keys["stock_id"].astype(str).str.zfill(4).unique())
    start_date = (
        pd.to_datetime(keys["asof_date"]).min() - pd.Timedelta(days=150)
    ).date().isoformat()
    end_date = (
        pd.to_datetime(keys["asof_date"]).max() - pd.Timedelta(days=1)
    ).date().isoformat()
    histories = load_local_histories(
        sqlite_path,
        stock_ids=stock_ids,
        start_date=start_date,
        end_date=end_date,
    )
    main_force = load_wide_panel(
        finlab_root / "main_force_chip" / "主力買賣超.pkl",
        stock_ids=stock_ids,
        start_date=start_date,
        end_date=end_date,
    )
    broker_count = load_wide_panel(
        finlab_root / "main_force_chip" / "買賣家數差.pkl",
        stock_ids=stock_ids,
        start_date=start_date,
        end_date=end_date,
    )
    features = build_pre_signal_feature_frame(
        keys,
        market_calendar=histories["market_calendar"],
        price_history=histories["price"],
        institutional_history=histories["institutional"],
        holder_history=histories["holder"],
        margin_history=histories["margin"],
        main_force_panel=main_force,
        broker_count_panel=broker_count,
    )
    assert_no_lookahead(features)
    scored = apply_shadow_strength_score(features, rules=load_frozen_rules(rules_csv))
    for column in FOUR_COMPONENT_EXPORT_COLUMNS:
        if column not in scored:
            scored[column] = np.nan
    output = scored[FOUR_COMPONENT_EXPORT_COLUMNS].copy()
    forbidden = [
        column
        for column in output.columns
        if column == "pre_margin_balance" or "foreign" in column
    ]
    if forbidden:
        raise AssertionError(f"forbidden four-component export columns: {forbidden}")
    return output


def summarize_future_kd_linkage(rows: pd.DataFrame) -> dict[str, Any]:
    mature = _as_bool(rows["future_kd_linkage_mature"])
    linked = _as_bool(rows["future_kd_confirmation_within_window"]) & mature
    return {
        "candidate_rows": int(len(rows)),
        "mature_candidate_rows": int(mature.sum()),
        "right_censored_candidate_rows": int((~mature).sum()),
        "linked_rows": int(linked.sum()),
        "linked_rate": _divide(int(linked.sum()), int(mature.sum())),
        "median_lead_trade_days": float(
            pd.to_numeric(
                rows.loc[linked, "future_kd_lead_trade_days"], errors="coerce"
            ).median()
        )
        if linked.any()
        else 0.0,
        "median_candidate_to_kd_return_pct": float(
            pd.to_numeric(
                rows.loc[linked, "candidate_to_future_kd_return_pct"], errors="coerce"
            ).median()
        )
        if linked.any()
        else 0.0,
    }


def build_four_component_bucket_metrics(rows: pd.DataFrame) -> pd.DataFrame:
    """Describe frozen four-component scores without using them for selection."""
    eligible = _as_bool(rows["primary_evaluation_eligible"])
    complete = _as_bool(rows["shadow_strength_complete"])
    frame = rows[eligible & complete].copy()
    records: list[dict[str, Any]] = []
    for score, group in frame.groupby("shadow_strength_score", sort=True):
        returns = pd.to_numeric(group["d5_adjusted_return_pct"], errors="coerce")
        linkage_mature = _as_bool(group["future_kd_linkage_mature"])
        linked = (
            _as_bool(group["future_kd_confirmation_within_window"])
            & linkage_mature
        )
        records.append(
            {
                "shadow_strength_score": float(score),
                "rows": int(len(group)),
                "d5_gain_ge10_rate": float(returns.ge(10).mean()),
                "d5_gain_ge20_rate": float(returns.ge(20).mean()),
                "d5_loss_rate": float(returns.lt(0).mean()),
                "avg_d5_adjusted_return_pct": float(returns.mean()),
                "median_d5_adjusted_return_pct": float(returns.median()),
                "future_kd_linkage_mature_rows": int(linkage_mature.sum()),
                "future_kd_linked_rate": _divide(
                    int(linked.sum()), int(linkage_mature.sum())
                ),
            }
        )
    return pd.DataFrame(records)


def evaluate_retrospective_edge_gate(
    metric: dict[str, Any],
    *,
    monthly: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, bool]:
    return {
        "minimum_candidate_rows": metric["candidate_rows"]
        >= int(config["minimum_candidate_rows"]),
        "precision_lift_vs_all": metric["precision_lift_vs_all"]
        >= float(config["minimum_precision_lift_vs_all"]),
        "balanced_accuracy": metric["balanced_accuracy_gain_ge10"]
        >= float(config["minimum_balanced_accuracy_gain_ge10"]),
        "loss_rate": metric["loss_rate"] <= float(config["maximum_d5_loss_rate"]),
        "every_month_nonempty": (
            not bool(config["require_every_month_nonempty"])
            or bool(monthly["candidate_rows"].gt(0).all())
        ),
    }


def database_source_audit(sqlite_path: Path) -> dict[str, Any]:
    with sqlite3.connect(sqlite_path) as connection:
        raw_max = connection.execute(
            "select max(date) from daily_ohlcv_features"
        ).fetchone()[0]
        pit_max = connection.execute(
            "select max(date) from stock_pit_sector_membership_daily"
        ).fetchone()[0]
        adjusted = connection.execute(
            "select max(date), max(asof_date) from tw_adjusted_ohlcv_daily"
        ).fetchone()
    return {
        "raw_price_max_date": str(raw_max),
        "pit_universe_max_date": str(pit_max),
        "adjusted_price_max_date": str(adjusted[0]),
        "adjusted_data_max_asof": str(adjusted[1]),
    }


def write_outputs(result: dict[str, Any], *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _safe_csv(
        result["candidate_rows"],
        output_dir / "zhu_walkline_full_market_early_start_candidates.csv",
    )
    _safe_csv(
        result["monthly_metrics"],
        output_dir / "zhu_walkline_full_market_early_start_monthly.csv",
    )
    _safe_csv(
        result["daily_metrics"],
        output_dir / "zhu_walkline_full_market_early_start_daily.csv",
    )
    _safe_csv(
        result["strength_buckets"],
        output_dir / "zhu_walkline_full_market_early_start_strength_buckets.csv",
    )
    (output_dir / "zhu_walkline_full_market_early_start_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_full_market_early_start_summary.md").write_text(
        render_markdown(result),
        encoding="utf-8",
    )


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    metric = summary["primary_metric"]
    linkage = summary["future_kd_linkage"]
    monthly = result["monthly_metrics"]
    strength_buckets = result["strength_buckets"]
    lines = [
        "# Zhu Walkline 全市場 D-10～D 提早起漲固定規則重播",
        "",
        "## 結論",
        "",
        f"- 全市場 retrospective edge：`{summary['retrospective_edge_observed']}`。",
        f"- 產生候選 {summary['generated_candidate_rows']} 筆；排除 "
        f"{summary['generated_candidate_rows'] - metric['candidate_rows']} 筆未來公司行動後，"
        f"primary evaluator 為 {metric['candidate_rows']} 筆；D+5 >=10% 精確率 "
        f"{metric['precision_gain_ge10']:.2%}；全體基準 "
        f"{metric['base_gain_ge10_rate']:.2%}；lift "
        f"{metric['precision_lift_vs_all']:.2f}x。",
        f"- 平衡準確率 {metric['balanced_accuracy_gain_ge10']:.2%}；"
        f"D+5 虧損率 {metric['loss_rate']:.2%}；中位回報 "
        f"{metric['median_d5_adjusted_return_pct']:.2f}%。",
        f"- 未來 2～10 交易日連到正式 KD D 日：{linkage['linked_rate']:.2%}；"
        f"中位提前 {linkage['median_lead_trade_days']:.1f} 日。",
        "- 本期已被先前 1,296 組事件條件式搜尋看過，只能作 retrospective gate，"
        "不能稱新 holdout 或 live 訊號。",
        "",
        "## 固定規則",
        "",
        f"```json\n{json.dumps(summary['fixed_rule'], ensure_ascii=False, indent=2)}\n```",
        "",
        "## 月份穩定性",
        "",
        "| 月份 | 候選 | 精確率 | lift | 召回率 | 平衡準確率 | 虧損率 | 中位回報 | 空訊號日 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in monthly.itertuples():
        lines.append(
            f"| {row.month} | {row.candidate_rows} | {row.precision_gain_ge10:.2%} | "
            f"{row.precision_lift_vs_all:.2f}x | {row.recall_gain_ge10:.2%} | "
            f"{row.balanced_accuracy_gain_ge10:.2%} | {row.loss_rate:.2%} | "
            f"{row.median_d5_adjusted_return_pct:.2f}% | {row.empty_candidate_days} |"
        )
    lines.extend(
        [
            "",
            "## 四項影子強度分桶",
            "",
            f"- 高分到低分的 D+5 >=10% 並非單調改善："
            f"`{summary['four_component_bucket_gain10_monotonic']}`。",
            "- 四項只作報告；此表不回頭改變固定技術候選。",
            "",
            "| 強度 | 筆數 | D+5 >=10% | D+5 >=20% | 虧損率 | 中位回報 | 未來KD連結率 |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in strength_buckets.itertuples():
        lines.append(
            f"| {row.shadow_strength_score:.0f} | {row.rows} | "
            f"{row.d5_gain_ge10_rate:.2%} | {row.d5_gain_ge20_rate:.2%} | "
            f"{row.d5_loss_rate:.2%} | {row.median_d5_adjusted_return_pct:.2f}% | "
            f"{row.future_kd_linked_rate:.2%} |"
        )
    lines.extend(
        [
            "",
            "## 資料與治理",
            "",
            f"- 原始價量最新：`{summary['source_audit']['raw_price_max_date']}`；"
            f"PIT universe 最新：`{summary['source_audit']['pit_universe_max_date']}`；"
            f"adjusted evaluator 最新：`{summary['source_audit']['adjusted_price_max_date']}`。",
            "- 選股只用 raw OHLCV 當日及以前資料；adjusted D+5、公司行動與未來 KD "
            "連結只存在 evaluator。",
            "- 四項影子強度只在候選選出後補算，未納入固定技術 mask。",
            f"- `research_scope={summary['research_scope']}`",
            f"- `live_deployable={summary['live_deployable']}`",
            f"- `next_required_gate={summary['next_required_gate']}`",
            f"- `promotion_decision={summary['promotion_decision']}`",
            "- `formal_champion_changed=False`",
            "- `formal_trade_effect=False`",
        ]
    )
    return "\n".join(lines) + "\n"


def _as_bool(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.lower().isin({"1", "true", "yes"})


def _divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _nondecreasing(values: pd.Series, *, tolerance: float = 1e-12) -> bool:
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    return bool(len(numeric) <= 1 or np.all(np.diff(numeric) >= -tolerance))


def _safe_csv(frame: pd.DataFrame, path: Path) -> None:
    output = frame.copy()
    for column in output.select_dtypes(include=["object", "string"]).columns:
        output[column] = output[column].fillna("")
    output.to_csv(path, index=False, encoding="utf-8-sig", na_rep="")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and bool(missing):
        return None
    return value


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config/zhu_walkline_full_market_early_start_replay.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_full_market_early_start_replay_2026_01_06",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_replay(
        config=_load_yaml(_repo_path(args.config)),
        output_dir=_repo_path(args.output_dir),
    )
    summary = result["summary"]
    print(f"candidate_rows={summary['primary_metric']['candidate_rows']}")
    print(
        "precision_gain_ge10="
        f"{summary['primary_metric']['precision_gain_ge10']:.6f}"
    )
    print(
        "balanced_accuracy_gain_ge10="
        f"{summary['primary_metric']['balanced_accuracy_gain_ge10']:.6f}"
    )
    print(f"retrospective_edge_observed={summary['retrospective_edge_observed']}")
    print(f"live_deployable={summary['live_deployable']}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
