"""Deep D-10 through D factor research with a full-market PIT challenger.

This sidecar keeps event-conditioned trajectories diagnostic-only.  The model
is trained and evaluated on every eligible point-in-time stock/date anchor and
uses next-open to D+5-close net returns as evaluator-only labels.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import gc
import hashlib
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

from abc_quant.features.d10_factor_panel import (  # noqa: E402
    INSTITUTIONAL_FACTOR_COLUMNS,
    TECHNICAL_FACTOR_COLUMNS,
    assert_factor_panel_point_in_time,
    build_d10_factor_panel,
)
from abc_quant.features.walkline_features import (  # noqa: E402
    compute_walkline_feature_history,
)
from abc_quant.validation.d10_factor_frontier import (  # noqa: E402
    D10FixedRule,
    SPLIT_ORDER,
    assign_label_maturity_purged_splits,
    build_event_factor_profile,
    build_factor_permutation_frontier,
    build_fixed_volume_threshold_table,
    d10_fixed_rule_mask,
    evaluate_frozen_factor_thresholds,
    prespecified_t1_mask,
)
from abc_quant.validation.d10_probability_challenger import (  # noqa: E402
    date_block_bootstrap_paired_delta,
    evaluate_probability_predictions,
    fit_binary_rule_calibrator,
    fit_probability_challenger,
    predict_binary_rule_proba,
    predict_probability_challenger,
)
from scripts.optimize_zhu_walkline_early_start_parameters import (  # noqa: E402
    apply_same_stock_cooldown,
)
from scripts.replay_zhu_walkline_full_market_early_start import (  # noqa: E402
    load_pit_universe,
    score_candidate_four_components,
)


MODE = "shadow_observation_only"
RAW_SCALE_TECHNICAL_EXCLUSIONS = {
    "volume_ma3",
    "volume_ma5",
    "volume_ma10",
    "volume_ma20",
    "volume_slope_3",
    "volume_slope_5",
    "volume_slope_10",
    "volume_slope_accel_3",
    "volume_slope_accel_5",
    "volume_slope_accel_10",
    "turnover_ma5_million_twd",
    "turnover_ma20_million_twd",
    "obv",
    "obv_slope_5",
}
MODEL_VARIANTS = ("TECH_BASE", "TECH_PLUS_INST")
RULE_VARIANTS = ("PRESPECIFIED_T1", "D10_FIXED_6", "KD_CONFIRMED_D")


def run_research(*, config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Run the frozen deep-factor pass and archive all evidence."""

    started = perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = config["analysis"]
    guards = config["universe_guards"]
    sqlite_path = Path(config["data"]["sqlite_path"])
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    timings: dict[str, float] = {}

    step = perf_counter()
    price_history = load_price_history(
        sqlite_path,
        start_date=analysis["history_start"],
        end_date=analysis["signal_end"],
    )
    institutional_history = load_institutional_history(
        sqlite_path,
        start_date=analysis["history_start"],
        end_date=analysis["signal_end"],
    )
    timings["load_raw_histories_seconds"] = perf_counter() - step

    step = perf_counter()
    walkline = compute_walkline_feature_history(
        price_history,
        asof_date=analysis["signal_end"],
    )
    factor_history = build_d10_factor_panel(
        price_history,
        asof_date=analysis["signal_end"],
        institutional_history=institutional_history,
        walkline_history=walkline,
    )
    factor_history = add_anchor_columns(factor_history, walkline)
    factor_history["prespecified_t1_raw"] = prespecified_t1_mask(
        factor_history,
        max_t5_volume_ratio_20=float(
            config["baselines"]["prespecified_t1"]["t5_max_volume_ratio_20"]
        ),
        min_t3_daily_return_pct=float(
            config["baselines"]["prespecified_t1"]["t3_min_daily_return_pct"]
        ),
        min_t1_daily_return_pct=float(
            config["baselines"]["prespecified_t1"]["t1_min_daily_return_pct"]
        ),
        min_t1_volume_ratio_20=float(
            config["baselines"]["prespecified_t1"]["t1_min_volume_ratio_20"]
        ),
    )
    fixed_rule = D10FixedRule(**config["baselines"]["d10_fixed_6"])
    factor_history["d10_fixed_6_raw"] = d10_fixed_rule_mask(
        factor_history, fixed_rule
    )
    assert_factor_panel_point_in_time(factor_history)
    timings["build_factor_history_seconds"] = perf_counter() - step
    del price_history, institutional_history, walkline
    gc.collect()

    step = perf_counter()
    signal_dates = pd.to_datetime(factor_history["observation_date"], errors="raise")
    signal_rows = factor_history.loc[
        signal_dates.between(
            pd.Timestamp(analysis["signal_start"]),
            pd.Timestamp(analysis["signal_end"]),
        )
    ].copy()
    signal_rows["date"] = pd.to_datetime(signal_rows["observation_date"])
    pit = load_pit_universe(
        sqlite_path,
        start_date=analysis["signal_start"],
        end_date=analysis["signal_end"],
        markets=[str(value) for value in guards["markets"]],
    )
    pit = pit.sort_values(["date", "stock_id", "pit_quality_rank"]).drop_duplicates(
        ["date", "stock_id"], keep="first"
    )
    if pit.duplicated(["date", "stock_id"]).any():
        raise AssertionError("PIT universe contains duplicate keys")
    universe = signal_rows.merge(
        pit,
        on=["date", "stock_id"],
        how="inner",
        validate="one_to_one",
    )
    effective = pd.to_datetime(universe["effective_source_date"], errors="coerce")
    listing = pd.to_datetime(universe["listing_date"], errors="coerce")
    if (effective.notna() & effective.gt(universe["date"])).any():
        raise AssertionError("PIT effective source date is after observation date")
    if (listing.notna() & listing.gt(universe["date"])).any():
        raise AssertionError("listing date is after observation date")
    eligible = universe[
        pd.to_numeric(universe["history_rows"], errors="coerce").ge(
            int(guards["minimum_history_rows"])
        )
        & pd.to_numeric(universe["avg_turnover_20_twd"], errors="coerce").ge(
            float(guards["minimum_avg_turnover_20_twd"])
        )
    ].copy()
    eligible["kd_confirmed_raw"] = confirmed_event_mask(
        eligible,
        path=_repo_path(config["data"]["confirmed_events_csv"]),
    )
    eligible["prespecified_t1"] = apply_outcome_free_cooldown(
        eligible,
        eligible["prespecified_t1_raw"],
        minimum_trade_days=int(guards["same_stock_cooldown_trade_days"]),
    )
    eligible["d10_fixed_6"] = apply_outcome_free_cooldown(
        eligible,
        eligible["d10_fixed_6_raw"],
        minimum_trade_days=int(guards["same_stock_cooldown_trade_days"]),
    )
    eligible["kd_confirmed_d"] = apply_outcome_free_cooldown(
        eligible,
        eligible["kd_confirmed_raw"],
        minimum_trade_days=int(guards["same_stock_cooldown_trade_days"]),
    )
    eligible["asof_date"] = eligible["date"].dt.strftime("%Y-%m-%d")
    timings["join_pit_and_build_baselines_seconds"] = perf_counter() - step

    technical_features = select_model_features(
        eligible,
        candidates=TECHNICAL_FACTOR_COLUMNS,
        start_date=config["splits"]["discovery_start"],
        end_date=config["splits"]["discovery_end"],
        minimum_coverage=float(config["factor_frontier"]["minimum_factor_coverage"]),
        exclusions=RAW_SCALE_TECHNICAL_EXCLUSIONS,
    )
    institutional_features = select_model_features(
        eligible,
        candidates=INSTITUTIONAL_FACTOR_COLUMNS,
        start_date=config["splits"]["discovery_start"],
        end_date=config["splits"]["discovery_end"],
        minimum_coverage=float(config["factor_frontier"]["minimum_factor_coverage"]),
    )
    manifest = build_factor_manifest(
        technical_features=technical_features,
        institutional_features=institutional_features,
        config=config,
    )

    step = perf_counter()
    adjusted = load_adjusted_execution_history(
        sqlite_path,
        start_date=analysis["signal_start"],
        end_date=analysis["signal_end"],
        horizon_trading_days=int(analysis["horizon_trading_days"]),
    )
    labeled = attach_market_calendar_execution_labels(
        eligible,
        adjusted_prices=adjusted,
        horizon_trading_days=int(analysis["horizon_trading_days"]),
        brokerage_fee_rate=float(
            config["execution"]["brokerage_fee_rate_each_side"]
        ),
        sell_tax_rate=float(config["execution"]["sell_tax_rate"]),
        one_way_slippage_rate=float(config["execution"]["one_way_slippage_rate"]),
    )
    labeled["observation_to_d5_adjusted_return_pct"] = (
        pd.to_numeric(labeled["exit_adj_close"], errors="coerce")
        / pd.to_numeric(labeled["signal_adj_close"], errors="coerce")
        - 1.0
    ) * 100.0
    label_mature = labeled["label_mature"].fillna(False).astype(bool)
    corporate_action = labeled["corporate_action_event_in_horizon"].fillna(False).astype(
        bool
    )
    primary = labeled[label_mature & ~corporate_action].copy()
    primary["target_gain_ge10"] = pd.to_numeric(
        primary["net_return_pct"], errors="coerce"
    ).ge(float(analysis["target_net_return_pct"]))
    primary["target_gain_ge20"] = pd.to_numeric(
        primary["net_return_pct"], errors="coerce"
    ).ge(float(analysis["large_gain_net_return_pct"]))
    split_windows = {
        split: (
            config["splits"][f"{split.lower()}_start"],
            config["splits"][f"{split.lower()}_end"],
        )
        for split in SPLIT_ORDER
    }
    primary["split"], split_audit = assign_label_maturity_purged_splits(
        primary,
        windows=split_windows,
    )
    modeling = primary[primary["split"].isin(SPLIT_ORDER)].copy()
    timings["attach_execution_labels_seconds"] = perf_counter() - step
    del adjusted, labeled, universe, signal_rows, pit
    gc.collect()

    step = perf_counter()
    model_result = fit_and_score_models(
        modeling,
        technical_features=technical_features,
        institutional_features=institutional_features,
        config=config,
    )
    modeling = model_result["rows"]
    modeling, operational_selection_audit = attach_operational_model_selections(
        modeling,
        candidate_rows=eligible,
        models=model_result["models"],
        thresholds=model_result["decision_thresholds"],
        minimum_trade_days=int(guards["same_stock_cooldown_trade_days"]),
    )
    del eligible
    gc.collect()
    probability_metrics, decision_metrics, monthly_metrics = evaluate_all_variants(
        modeling,
        model_thresholds=model_result["decision_thresholds"],
        config=config,
    )
    bootstrap = build_holdout_bootstrap(modeling, config=config)
    coefficients = build_coefficient_table(
        model_result["models"],
        technical_features=technical_features,
        institutional_features=institutional_features,
    )
    timings["fit_and_evaluate_models_seconds"] = perf_counter() - step

    step = perf_counter()
    discovery = modeling[modeling["split"].eq("DISCOVERY")]
    frontier = build_factor_permutation_frontier(
        discovery,
        feature_columns=[*technical_features, *institutional_features],
        target_column="target_gain_ge10",
        return_column="net_return_pct",
        date_column="asof_date",
        repetitions=int(config["factor_frontier"]["permutation_repetitions"]),
        random_seed=int(config["factor_frontier"]["random_seed"]),
        minimum_coverage=float(config["factor_frontier"]["minimum_factor_coverage"]),
        lower_quantile=float(config["factor_frontier"]["discovery_quantiles"][0]),
        upper_quantile=float(config["factor_frontier"]["discovery_quantiles"][1]),
    )
    frontier_splits = evaluate_frozen_factor_thresholds(
        modeling,
        frontier,
        split_column="split",
        target_column="target_gain_ge10",
        return_column="net_return_pct",
    )
    volume_thresholds = build_fixed_volume_threshold_table(
        modeling,
        feature_columns=["volume_ratio_5", "volume_ratio_20"],
        thresholds=config["factor_frontier"]["volume_ratio_fixed_thresholds"],
        split_column="split",
        target_column="target_gain_ge10",
        return_column="net_return_pct",
    )
    timings["factor_frontier_seconds"] = perf_counter() - step

    step = perf_counter()
    trajectory, trajectory_profile, trajectory_alerts = build_event_diagnostics(
        path=_repo_path(config["data"]["event_trajectory_csv"]),
        factor_history=factor_history,
        models=model_result["models"],
        technical_features=technical_features,
        institutional_features=institutional_features,
        thresholds=model_result["decision_thresholds"],
    )
    timings["event_trajectory_seconds"] = perf_counter() - step
    del factor_history
    gc.collect()

    step = perf_counter()
    selected_rows = build_ranked_holdout_candidates(
        modeling,
        sqlite_path=sqlite_path,
        finlab_root=Path(config["data"]["finlab_items_root"]),
        rules_csv=_repo_path(config["data"]["shadow_strength_rules_csv"]),
    )
    timings["four_component_ranking_seconds"] = perf_counter() - step

    source_audit = build_source_audit(
        sqlite_path,
        signal_start=analysis["signal_start"],
        signal_end=analysis["signal_end"],
        modeling=modeling,
    )
    comparison = build_comparison_decision(
        probability_metrics=probability_metrics,
        decision_metrics=decision_metrics,
        monthly_metrics=monthly_metrics,
        bootstrap=bootstrap,
        minimum_rows=int(config["factor_frontier"]["minimum_selected_rows_per_split"]),
        trajectory_alerts=trajectory_alerts,
        modeling_rows=modeling,
    )
    timings["total_seconds"] = perf_counter() - started
    summary = {
        "purpose": "full_market_d10_deep_factor_challenger",
        "market": analysis["market"],
        "currency": analysis["currency"],
        "timezone": analysis["timezone"],
        "as_of": analysis["signal_end"],
        "horizon": "next adjusted open to fifth adjusted close",
        "target": f"net_return_pct >= {analysis['target_net_return_pct']}",
        "factor_manifest": manifest,
        "technical_feature_count": len(technical_features),
        "institutional_feature_count": len(institutional_features),
        "eligible_model_rows": int(len(modeling)),
        "split_rows": {
            split: int(modeling["split"].eq(split).sum()) for split in SPLIT_ORDER
        },
        "split_audit": split_audit.to_dict("records"),
        "model_selection": model_result["model_selection"],
        "decision_thresholds": model_result["decision_thresholds"],
        "operational_selection_audit": operational_selection_audit.to_dict(
            "records"
        ),
        "comparison": comparison,
        "top_factor_frontier": frontier.head(20).to_dict("records"),
        "source_audit": source_audit,
        "cost_assumptions": config["execution"],
        "timings_seconds": timings,
        "four_component_role": (
            "main force, no upper-tail supply, volume ratio, and five-day margin "
            "change remain the report ordering only and are not model inputs"
        ),
        "institutional_boundary": (
            "aligned net-flow ratios are lagged at least one observation day; raw "
            "foreign shares and raw margin balance are excluded"
        ),
        "factor_frontier_statistical_boundary": (
            "within-date permutations preserve daily regime prevalence but do not "
            "fully preserve stock, sector, or overlapping D+5 serial dependence; "
            "single-factor p-values are screening evidence only"
        ),
        "research_scope": config["governance"]["research_scope"],
        "selection_period_previously_inspected": bool(
            config["governance"]["selection_period_previously_inspected"]
        ),
        "live_deployable": False,
        "next_required_gate": config["governance"]["next_required_gate"],
        "promotion_decision": config["governance"]["promotion_decision"],
        "mode": MODE,
        "formal_champion_changed": False,
        "formal_trade_effect": False,
    }
    result = {
        "summary": summary,
        "split_audit": split_audit,
        "probability_metrics": probability_metrics,
        "decision_metrics": decision_metrics,
        "monthly_metrics": monthly_metrics,
        "bootstrap": bootstrap,
        "coefficients": coefficients,
        "factor_frontier": frontier,
        "factor_frontier_splits": frontier_splits,
        "volume_thresholds": volume_thresholds,
        "trajectory": trajectory,
        "trajectory_profile": trajectory_profile,
        "trajectory_alerts": trajectory_alerts,
        "selected_rows": selected_rows,
        "operational_selection_audit": operational_selection_audit,
        "modeling_rows": modeling[
            list(
                dict.fromkeys(
                    [
                        "asof_date",
                        "observation_date",
                        "stock_id",
                        "technical_source_date",
                        "institutional_source_date",
                        "split",
                        *technical_features,
                        *institutional_features,
                        "prespecified_t1",
                        "d10_fixed_6",
                        "kd_confirmed_d",
                        "prob_all_eligible",
                        "prob_prespecified_t1",
                        "prob_d10_fixed_6",
                        "prob_kd_confirmed_d",
                        "prob_tech_base",
                        "prob_tech_plus_inst",
                        "tech_base_threshold",
                        "tech_plus_inst_threshold",
                        "tech_base_matched_t1",
                        "tech_plus_inst_matched_t1",
                        "entry_date",
                        "exit_date",
                        "entry_locked_limit_up",
                        "net_return_pct",
                        "target_gain_ge10",
                        "target_gain_ge20",
                    ]
                )
            )
        ].copy(),
    }
    write_outputs(result, output_dir=output_dir)
    return result


def load_price_history(
    sqlite_path: Path, *, start_date: str, end_date: str
) -> pd.DataFrame:
    query = """
        select date, stock_id, open, high, low, close, volume
        from daily_ohlcv_features
        where date between ? and ? and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query, connection, params=[start_date, end_date], parse_dates=["date"]
        )


def load_institutional_history(
    sqlite_path: Path, *, start_date: str, end_date: str
) -> pd.DataFrame:
    query = """
        select date, stock_id, foreign_net_buy_shares, trust_net_buy_shares,
               dealer_net_buy_shares, institutional_net_buy_shares,
               flow_available, flow_source
        from tw_institutional_flow_moving_averages_price_aligned_daily
        where date between ? and ? and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query, connection, params=[start_date, end_date], parse_dates=["date"]
        )


def load_adjusted_execution_history(
    sqlite_path: Path,
    *,
    start_date: str,
    end_date: str,
    horizon_trading_days: int,
) -> pd.DataFrame:
    buffer_days = max(60, horizon_trading_days * 4)
    query = """
        select date, stock_id, adj_open, adj_high, adj_low, adj_close,
               adj_previous_close, adjustment_factor, factor_event_count,
               asof_date as adjusted_data_asof
        from tw_adjusted_ohlcv_daily
        where date >= ? and date <= date(?, ?) and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, end_date, f"+{buffer_days} day"],
            parse_dates=["date"],
        )


def attach_market_calendar_execution_labels(
    frame: pd.DataFrame,
    *,
    adjusted_prices: pd.DataFrame,
    horizon_trading_days: int,
    brokerage_fee_rate: float,
    sell_tax_rate: float,
    one_way_slippage_rate: float,
) -> pd.DataFrame:
    """Attach next-open/D+N-close labels on the shared Taiwan market calendar.

    A suspended stock has no executable price on the exact market date and is
    therefore left label-ineligible.  It is never shifted to a much later
    stock-specific fifth bar, which would silently change the target horizon.
    """

    if horizon_trading_days < 2:
        raise ValueError("horizon_trading_days must be at least 2")
    output = frame.copy()
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["asof_date"] = pd.to_datetime(output["asof_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    prices = adjusted_prices.copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="raise")
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    prices = prices.sort_values(["date", "stock_id"]).drop_duplicates(
        ["date", "stock_id"], keep="last"
    )
    numeric_columns = [
        "adj_open",
        "adj_high",
        "adj_low",
        "adj_close",
        "adj_previous_close",
        "adjustment_factor",
        "factor_event_count",
    ]
    for column in numeric_columns:
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    calendar = pd.Series(sorted(prices["date"].dropna().unique()))
    mapping = pd.DataFrame(
        {
            "asof_date": pd.to_datetime(calendar).dt.strftime("%Y-%m-%d"),
            "entry_date": pd.to_datetime(calendar.shift(-1)).dt.strftime("%Y-%m-%d"),
            "exit_date": pd.to_datetime(calendar.shift(-horizon_trading_days)).dt.strftime(
                "%Y-%m-%d"
            ),
        }
    )
    output = output.merge(mapping, on="asof_date", how="left", validate="many_to_one")

    signal = prices[
        ["date", "stock_id", "adj_close", "adjustment_factor", "factor_event_count"]
    ].rename(
        columns={
            "date": "asof_date",
            "adj_close": "signal_adj_close",
            "adjustment_factor": "signal_adjustment_factor",
            "factor_event_count": "signal_factor_event_count",
        }
    )
    signal["asof_date"] = signal["asof_date"].dt.strftime("%Y-%m-%d")
    entry = prices[
        [
            "date",
            "stock_id",
            "adj_open",
            "adj_high",
            "adj_low",
            "adj_previous_close",
        ]
    ].rename(
        columns={
            "date": "entry_date",
            "adj_open": "entry_adj_open",
            "adj_high": "entry_adj_high",
            "adj_low": "entry_adj_low",
            "adj_previous_close": "entry_adj_previous_close",
        }
    )
    entry["entry_date"] = entry["entry_date"].dt.strftime("%Y-%m-%d")
    exit_prices = prices[
        ["date", "stock_id", "adj_close", "adjustment_factor", "factor_event_count"]
    ].rename(
        columns={
            "date": "exit_date",
            "adj_close": "exit_adj_close",
            "adjustment_factor": "exit_adjustment_factor",
            "factor_event_count": "exit_factor_event_count",
        }
    )
    exit_prices["exit_date"] = exit_prices["exit_date"].dt.strftime("%Y-%m-%d")
    output = output.merge(signal, on=["asof_date", "stock_id"], how="left")
    output = output.merge(entry, on=["entry_date", "stock_id"], how="left")
    output = output.merge(
        exit_prices, on=["exit_date", "stock_id"], how="left"
    )

    entry_open = pd.to_numeric(output["entry_adj_open"], errors="coerce")
    entry_high = pd.to_numeric(output["entry_adj_high"], errors="coerce")
    entry_low = pd.to_numeric(output["entry_adj_low"], errors="coerce")
    entry_previous = pd.to_numeric(
        output["entry_adj_previous_close"], errors="coerce"
    )
    signal_close = pd.to_numeric(output["signal_adj_close"], errors="coerce")
    exit_close = pd.to_numeric(output["exit_adj_close"], errors="coerce")
    output["gross_return_pct"] = (exit_close / entry_open - 1.0) * 100.0
    buy_multiplier = 1.0 + brokerage_fee_rate + one_way_slippage_rate
    sell_multiplier = 1.0 - brokerage_fee_rate - sell_tax_rate - one_way_slippage_rate
    output["net_return_pct"] = (
        exit_close * sell_multiplier / (entry_open * buy_multiplier) - 1.0
    ) * 100.0
    output["entry_gap_pct"] = (entry_open / signal_close - 1.0) * 100.0
    output["entry_return_vs_previous_close_pct"] = (
        entry_open / entry_previous - 1.0
    ) * 100.0
    entry_range_pct = (entry_high - entry_low).abs() / entry_previous * 100.0
    output["entry_locked_limit_up"] = (
        entry_open.notna()
        & entry_previous.gt(0.0)
        & output["entry_return_vs_previous_close_pct"].ge(9.5)
        & entry_range_pct.le(0.1)
    )
    signal_factor = pd.to_numeric(
        output["signal_adjustment_factor"], errors="coerce"
    )
    exit_factor = pd.to_numeric(output["exit_adjustment_factor"], errors="coerce")
    output["corporate_action_event_in_horizon"] = (
        signal_factor.notna()
        & exit_factor.notna()
        & signal_factor.sub(exit_factor).abs().gt(1e-12)
    )
    output["label_mature"] = entry_open.notna() & exit_close.notna()
    return output


def add_anchor_columns(
    factor_panel: pd.DataFrame, walkline_history: pd.DataFrame
) -> pd.DataFrame:
    """Attach causal columns needed by universe guards and frozen baselines."""

    history = walkline_history.copy().sort_values(["stock_id", "date"])
    grouped = history.groupby("stock_id", sort=False, group_keys=False)
    history["signal_trade_index"] = grouped.cumcount().astype(int)
    history["history_rows"] = history["signal_trade_index"] + 1
    history["return_1d_pct"] = pd.to_numeric(history["return_1d"], errors="coerce") * 100.0
    history["distance_from_trailing_5d_low_pct"] = (
        pd.to_numeric(history["close"], errors="coerce")
        / pd.to_numeric(history["swing_low_1"], errors="coerce")
        - 1.0
    ) * 100.0
    history["avg_turnover_20_twd"] = pd.to_numeric(
        history["amount_ma20"], errors="coerce"
    )
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
        "return_1d_pct",
        "distance_from_trailing_5d_low_pct",
        "avg_turnover_20_twd",
    ]
    anchors = history[columns].rename(columns={"date": "observation_date"})
    return factor_panel.merge(
        anchors,
        on=["observation_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )


def confirmed_event_mask(rows: pd.DataFrame, *, path: Path) -> pd.Series:
    events = pd.read_csv(path, dtype={"stock_id": str})
    events["asof_date"] = pd.to_datetime(events["asof_date"]).dt.strftime("%Y-%m-%d")
    events["stock_id"] = events["stock_id"].astype(str).str.zfill(4)
    keys = set(events[["asof_date", "stock_id"]].astype(str).agg("|".join, axis=1))
    row_keys = pd.DataFrame(
        {
            "asof_date": pd.to_datetime(rows["date"]).dt.strftime("%Y-%m-%d"),
            "stock_id": rows["stock_id"].astype(str).str.zfill(4),
        },
        index=rows.index,
    ).astype(str).agg("|".join, axis=1)
    return row_keys.isin(keys)


def apply_outcome_free_cooldown(
    rows: pd.DataFrame, mask: pd.Series, *, minimum_trade_days: int
) -> pd.Series:
    candidates = rows.loc[mask.fillna(False)].copy()
    if candidates.empty:
        return pd.Series(False, index=rows.index)
    candidates["asof_date"] = pd.to_datetime(candidates["date"])
    cooled = apply_same_stock_cooldown(
        candidates,
        minimum_trade_days=minimum_trade_days,
    )
    kept = cooled[cooled["same_stock_cooldown"]].copy()
    keys = set(
        pd.DataFrame(
            {
                "asof_date": pd.to_datetime(kept["asof_date"]).dt.strftime("%Y-%m-%d"),
                "stock_id": kept["stock_id"].astype(str).str.zfill(4),
            }
        )
        .astype(str)
        .agg("|".join, axis=1)
    )
    row_keys = pd.DataFrame(
        {
            "asof_date": pd.to_datetime(rows["date"]).dt.strftime("%Y-%m-%d"),
            "stock_id": rows["stock_id"].astype(str).str.zfill(4),
        },
        index=rows.index,
    ).astype(str).agg("|".join, axis=1)
    return row_keys.isin(keys)


def select_model_features(
    rows: pd.DataFrame,
    *,
    candidates: tuple[str, ...],
    start_date: str,
    end_date: str,
    minimum_coverage: float,
    exclusions: set[str] | None = None,
) -> list[str]:
    dates = pd.to_datetime(rows["date"], errors="raise")
    discovery = rows.loc[dates.between(pd.Timestamp(start_date), pd.Timestamp(end_date))]
    excluded = exclusions or set()
    selected: list[str] = []
    for column in candidates:
        if column in excluded or column not in discovery:
            continue
        coverage = pd.to_numeric(discovery[column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).notna().mean()
        if coverage >= minimum_coverage:
            selected.append(column)
    if not selected:
        raise ValueError("no model features passed discovery-only coverage")
    return selected


def build_factor_manifest(
    *,
    technical_features: list[str],
    institutional_features: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "technical_features": technical_features,
        "institutional_features": institutional_features,
        "technical_source_boundary": "source_date <= observation_date",
        "institutional_source_boundary": "source_date < observation_date",
        "raw_institutional_shares_exported": False,
        "raw_margin_balance_exported": False,
        "volume_thresholds": config["factor_frontier"][
            "volume_ratio_fixed_thresholds"
        ],
        "mutation_id": config["model"]["mutation_id"],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {**payload, "sha256": hashlib.sha256(encoded).hexdigest()}


def fit_and_score_models(
    rows: pd.DataFrame,
    *,
    technical_features: list[str],
    institutional_features: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Fit split-locked probability models and score every evaluation row."""

    split_rows = {
        split: rows.loc[rows["split"].eq(split)].copy() for split in SPLIT_ORDER
    }
    if any(frame.empty for frame in split_rows.values()):
        empty = [split for split, frame in split_rows.items() if frame.empty]
        raise ValueError(f"empty model splits after label-maturity purge: {empty}")
    target = "target_gain_ge10"
    model_config = config["model"]
    specifications = {
        "TECH_BASE": technical_features,
        "TECH_PLUS_INST": [*technical_features, *institutional_features],
    }
    fitted: dict[str, Any] = {}
    selection: dict[str, Any] = {}
    thresholds: dict[str, float] = {}
    for variant, features in specifications.items():
        challenger = fit_probability_challenger(
            split_rows["DISCOVERY"],
            split_rows["DISCOVERY"][target].astype(int),
            split_rows["VALIDATION"],
            split_rows["VALIDATION"][target].astype(int),
            split_rows["CALIBRATION"],
            split_rows["CALIBRATION"][target].astype(int),
            feature_names=features,
            l2_grid=model_config["lambda_grid"],
            selection_metric="brier",
            max_iterations=int(model_config["maximum_iterations"]),
            tolerance=float(model_config["tolerance"]),
        )
        probability_column = f"prob_{variant.lower()}"
        rows[probability_column] = predict_probability_challenger(challenger, rows)
        validation = rows["split"].eq("VALIDATION")
        reference_count = int(rows.loc[validation, "prespecified_t1"].sum())
        thresholds[variant] = _coverage_matched_threshold(
            rows.loc[validation, probability_column],
            reference_count=reference_count,
        )
        fitted[variant] = challenger
        selection[variant] = {
            "feature_count": len(features),
            "selected_l2_penalty": float(challenger.logistic_model.l2_penalty),
            "optimizer_converged": bool(challenger.logistic_model.converged),
            "optimizer_iterations": int(challenger.logistic_model.iterations),
            "platt_converged": bool(challenger.platt_calibrator.converged),
            "platt_iterations": int(challenger.platt_calibrator.iterations),
            "validation_scores": [
                asdict(score) for score in challenger.validation_scores
            ],
        }

    discovery = rows["split"].eq("DISCOVERY")
    base_rate = float(rows.loc[discovery, target].mean())
    rows["prob_all_eligible"] = base_rate
    rule_columns = {
        "PRESPECIFIED_T1": "prespecified_t1",
        "D10_FIXED_6": "d10_fixed_6",
        "KD_CONFIRMED_D": "kd_confirmed_d",
    }
    rule_calibrators: dict[str, Any] = {}
    for variant, column in rule_columns.items():
        calibrator = fit_binary_rule_calibrator(
            rows.loc[discovery, column],
            rows.loc[discovery, target].astype(int),
        )
        rows[f"prob_{variant.lower()}"] = predict_binary_rule_proba(
            calibrator, rows[column]
        )
        rule_calibrators[variant] = calibrator
        selection[variant] = asdict(calibrator)

    return {
        "rows": rows,
        "models": fitted,
        "rule_calibrators": rule_calibrators,
        "model_selection": selection,
        "decision_thresholds": thresholds,
    }


def _coverage_matched_threshold(
    probabilities: pd.Series, *, reference_count: int
) -> float:
    scores = pd.to_numeric(probabilities, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    if scores.empty or reference_count <= 0:
        return 1.0
    if reference_count >= len(scores):
        return 0.0
    ordered = np.sort(scores.to_numpy(dtype=float))[::-1]
    return float(np.clip(ordered[reference_count - 1], 0.0, 1.0))


def attach_operational_model_selections(
    modeling: pd.DataFrame,
    *,
    candidate_rows: pd.DataFrame,
    models: dict[str, Any],
    thresholds: dict[str, float],
    minimum_trade_days: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select models on the full label-free universe with the same cooldown.

    The daily matched quota is the already-cooled T-1 count.  Ranking and
    cooldown are applied before evaluator labels, corporate-action exclusions,
    and split purges, so future availability cannot influence membership.
    """

    candidates = candidate_rows.copy()
    candidates["asof_date"] = pd.to_datetime(candidates["asof_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    if candidates.duplicated(["asof_date", "stock_id"]).any():
        raise ValueError("operational candidate universe contains duplicate stock dates")
    selection_columns: list[str] = []
    audit_frames: list[pd.DataFrame] = []
    for variant, challenger in models.items():
        prefix = variant.lower()
        probability_column = f"operational_prob_{prefix}"
        candidates[probability_column] = predict_probability_challenger(
            challenger, candidates
        )
        threshold_column = f"{prefix}_threshold"
        candidates[threshold_column] = apply_outcome_free_cooldown(
            candidates,
            candidates[probability_column].ge(thresholds[variant]),
            minimum_trade_days=minimum_trade_days,
        )
        matched_column = f"{prefix}_matched_t1"
        matched, audit = daily_matched_top_k_with_cooldown(
            candidates,
            score_column=probability_column,
            reference_column="prespecified_t1",
            minimum_trade_days=minimum_trade_days,
        )
        candidates[matched_column] = matched
        audit.insert(0, "variant", variant)
        audit_frames.append(audit)
        selection_columns.extend([threshold_column, matched_column])

    selections = candidates[["asof_date", "stock_id", *selection_columns]].copy()
    output = modeling.drop(columns=selection_columns, errors="ignore").merge(
        selections,
        on=["asof_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    for column in selection_columns:
        output[column] = output[column].fillna(False).astype(bool)
    audit = pd.concat(audit_frames, ignore_index=True)
    return output, audit


def daily_matched_top_k_with_cooldown(
    rows: pd.DataFrame,
    *,
    score_column: str,
    reference_column: str,
    minimum_trade_days: int,
) -> tuple[pd.Series, pd.DataFrame]:
    """Rank each day, enforce prior selections, then fill the reference quota."""

    required = {
        "asof_date",
        "stock_id",
        "signal_trade_index",
        score_column,
        reference_column,
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"daily cooldown matcher missing columns: {sorted(missing)}")
    work = rows[
        [
            "asof_date",
            "stock_id",
            "signal_trade_index",
            score_column,
            reference_column,
        ]
    ].copy()
    work["asof_date"] = pd.to_datetime(work["asof_date"], errors="raise")
    work["stock_id"] = work["stock_id"].astype(str).str.zfill(4)
    work["signal_trade_index"] = pd.to_numeric(
        work["signal_trade_index"], errors="raise"
    )
    work[score_column] = pd.to_numeric(work[score_column], errors="coerce")
    if work[score_column].isna().any() or np.isinf(work[score_column]).any():
        raise ValueError("operational model scores must be finite")
    work[reference_column] = work[reference_column].fillna(False).astype(bool)
    selected = pd.Series(False, index=rows.index, dtype=bool)
    last_selected_trade_index: dict[str, float] = {}
    audit: list[dict[str, Any]] = []
    for asof_date, daily in work.groupby("asof_date", sort=True):
        desired = int(daily[reference_column].sum())
        ranked = daily.sort_values(
            [score_column, "stock_id"], ascending=[False, True], kind="mergesort"
        )
        available = 0
        accepted_indices: list[Any] = []
        for row in ranked.itertuples():
            prior = last_selected_trade_index.get(str(row.stock_id))
            can_select = (
                prior is None
                or float(row.signal_trade_index) - prior >= minimum_trade_days
            )
            if not can_select:
                continue
            available += 1
            if len(accepted_indices) >= desired:
                continue
            accepted_indices.append(row.Index)
            last_selected_trade_index[str(row.stock_id)] = float(
                row.signal_trade_index
            )
        selected.loc[accepted_indices] = True
        audit.append(
            {
                "asof_date": asof_date.strftime("%Y-%m-%d"),
                "reference_quota": desired,
                "selected_rows": len(accepted_indices),
                "quota_shortfall": max(0, desired - len(accepted_indices)),
                "cooldown_eligible_rows": available,
            }
        )
    selected_rows = work.loc[selected]
    violations = 0
    for _, group in selected_rows.sort_values(
        ["stock_id", "asof_date"]
    ).groupby("stock_id", sort=False):
        differences = group["signal_trade_index"].diff().dropna()
        violations += int(differences.lt(minimum_trade_days).sum())
    if violations:
        raise AssertionError(f"operational cooldown violations: {violations}")
    return selected, pd.DataFrame(audit)


def evaluate_all_variants(
    rows: pd.DataFrame,
    *,
    model_thresholds: dict[str, float],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compare calibrated probabilities and frozen decision views by split."""

    probability_columns = {
        "ALL_ELIGIBLE": "prob_all_eligible",
        "PRESPECIFIED_T1": "prob_prespecified_t1",
        "D10_FIXED_6": "prob_d10_fixed_6",
        "KD_CONFIRMED_D": "prob_kd_confirmed_d",
        "TECH_BASE": "prob_tech_base",
        "TECH_PLUS_INST": "prob_tech_plus_inst",
    }
    probability_records: list[dict[str, Any]] = []
    for split in SPLIT_ORDER:
        frame = rows.loc[rows["split"].eq(split)]
        all_dates = sorted(frame["asof_date"].unique())
        for variant, column in probability_columns.items():
            threshold = model_thresholds.get(variant, 0.5)
            if variant == "ALL_ELIGIBLE":
                threshold = 0.0
            metrics = evaluate_probability_predictions(
                frame["target_gain_ge10"].astype(int),
                frame[column],
                threshold=threshold,
                net_returns=frame["net_return_pct"],
                dates=frame["asof_date"],
                all_dates=all_dates,
                ece_bin_count=int(config["model"]["ece_bins"]),
                tail_loss_threshold=float(
                    config["analysis"]["tail_loss_net_return_pct"]
                ),
            )
            probability_records.append(
                {"split": split, "variant": variant, "threshold": threshold, **metrics}
            )

    required_decisions = {
        "tech_base_threshold",
        "tech_plus_inst_threshold",
        "tech_base_matched_t1",
        "tech_plus_inst_matched_t1",
    }
    missing_decisions = required_decisions - set(rows.columns)
    if missing_decisions:
        raise ValueError(
            "operational model selections missing: "
            + ", ".join(sorted(missing_decisions))
        )

    decision_columns = {
        "ALL_ELIGIBLE": pd.Series(True, index=rows.index),
        "PRESPECIFIED_T1": rows["prespecified_t1"],
        "D10_FIXED_6": rows["d10_fixed_6"],
        "KD_CONFIRMED_D": rows["kd_confirmed_d"],
        "TECH_BASE_THRESHOLD": rows["tech_base_threshold"],
        "TECH_PLUS_INST_THRESHOLD": rows["tech_plus_inst_threshold"],
        "TECH_BASE_MATCHED_T1": rows["tech_base_matched_t1"],
        "TECH_PLUS_INST_MATCHED_T1": rows["tech_plus_inst_matched_t1"],
    }
    locked = rows["entry_locked_limit_up"].fillna(False).astype(bool)
    exclude_locked = bool(
        config["execution"]["exclude_entry_locked_limit_up_from_tradable_view"]
    )
    decision_records: list[dict[str, Any]] = []
    monthly_records: list[dict[str, Any]] = []
    for split in SPLIT_ORDER:
        split_mask = rows["split"].eq(split)
        split_rows = rows.loc[split_mask]
        for variant, full_mask in decision_columns.items():
            selected = full_mask.loc[split_rows.index].fillna(False).astype(bool)
            views = {"PRIMARY": selected}
            if exclude_locked:
                views["TRADABLE"] = selected & ~locked.loc[split_rows.index]
            for view, view_mask in views.items():
                decision_records.append(
                    _decision_metrics(
                        split_rows,
                        view_mask,
                        split=split,
                        variant=variant,
                        view=view,
                        tail_loss_threshold=float(
                            config["analysis"]["tail_loss_net_return_pct"]
                        ),
                    )
                )
            month = pd.to_datetime(split_rows["asof_date"]).dt.to_period("M").astype(str)
            for month_value in sorted(month.unique()):
                month_rows = split_rows.loc[month.eq(month_value)]
                month_selected = selected.loc[month_rows.index]
                if exclude_locked:
                    month_selected &= ~locked.loc[month_rows.index]
                monthly_records.append(
                    _decision_metrics(
                        month_rows,
                        month_selected,
                        split=split,
                        variant=variant,
                        view="TRADABLE" if exclude_locked else "PRIMARY",
                        tail_loss_threshold=float(
                            config["analysis"]["tail_loss_net_return_pct"]
                        ),
                        month=month_value,
                    )
                )
    return (
        pd.DataFrame(probability_records),
        pd.DataFrame(decision_records),
        pd.DataFrame(monthly_records),
    )


def _decision_metrics(
    rows: pd.DataFrame,
    selected: pd.Series,
    *,
    split: str,
    variant: str,
    view: str,
    tail_loss_threshold: float,
    month: str | None = None,
) -> dict[str, Any]:
    labels = rows["target_gain_ge10"].astype(bool)
    chosen = selected.fillna(False).astype(bool)
    selected_rows = rows.loc[chosen]
    returns = pd.to_numeric(selected_rows["net_return_pct"], errors="coerce").dropna()
    true_positive = int((chosen & labels).sum())
    selected_count = int(chosen.sum())
    positive_count = int(labels.sum())
    true_negative = int((~chosen & ~labels).sum())
    negative_count = int((~labels).sum())
    precision = _safe_divide(true_positive, selected_count)
    recall = _safe_divide(true_positive, positive_count)
    specificity = _safe_divide(true_negative, negative_count)
    base_rate = _safe_divide(positive_count, len(rows))
    tail_count = max(1, int(np.ceil(0.05 * len(returns)))) if len(returns) else 0
    record = {
        "split": split,
        "variant": variant,
        "view": view,
        "rows": int(len(rows)),
        "selected_rows": selected_count,
        "coverage": _safe_divide(selected_count, len(rows)),
        "base_gain_ge10_rate": base_rate,
        "precision_gain_ge10": precision,
        "precision_lift_vs_split": _safe_divide(precision, base_rate),
        "recall_gain_ge10": recall,
        "balanced_accuracy": (
            float((recall + specificity) / 2.0)
            if np.isfinite(recall) and np.isfinite(specificity)
            else np.nan
        ),
        "gain_ge20_rate": float(selected_rows["target_gain_ge20"].mean())
        if selected_count
        else np.nan,
        "loss_rate": float(returns.lt(0.0).mean()) if len(returns) else np.nan,
        "tail_loss_rate": float(returns.le(tail_loss_threshold).mean())
        if len(returns)
        else np.nan,
        "mean_net_return_pct": float(returns.mean()) if len(returns) else np.nan,
        "median_net_return_pct": float(returns.median()) if len(returns) else np.nan,
        "cvar_5_pct": float(np.sort(returns.to_numpy())[:tail_count].mean())
        if tail_count
        else np.nan,
        "selected_dates": int(selected_rows["asof_date"].nunique()),
        "empty_dates": int(rows["asof_date"].nunique() - selected_rows["asof_date"].nunique()),
    }
    if month is not None:
        record["month"] = month
    return record


def _safe_divide(numerator: float | int, denominator: float | int) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return float(numerator / denominator)


def build_holdout_bootstrap(
    rows: pd.DataFrame, *, config: dict[str, Any]
) -> pd.DataFrame:
    """Run date-block paired uncertainty checks on the untouched holdout."""

    holdout = rows.loc[rows["split"].eq("HOLDOUT")].copy()
    if config["execution"]["exclude_entry_locked_limit_up_from_tradable_view"]:
        holdout = holdout.loc[
            ~holdout["entry_locked_limit_up"].fillna(False).astype(bool)
        ].copy()
    if holdout.empty:
        return pd.DataFrame()
    repetitions = int(config["factor_frontier"]["bootstrap_repetitions"])
    seed = int(config["factor_frontier"]["random_seed"])
    block_length = min(
        int(config["factor_frontier"].get("bootstrap_block_length_days", 5)),
        int(holdout["asof_date"].nunique()),
    )
    dates = holdout["asof_date"]
    labels = holdout["target_gain_ge10"].astype(int)
    returns = pd.to_numeric(holdout["net_return_pct"], errors="raise")
    comparisons = [
        (
            "TECH_PLUS_INST_vs_TECH_BASE",
            holdout["prob_tech_plus_inst"],
            holdout["prob_tech_base"],
            "brier",
            None,
        ),
        (
            "TECH_PLUS_INST_vs_TECH_BASE",
            holdout["prob_tech_plus_inst"],
            holdout["prob_tech_base"],
            "logloss",
            None,
        ),
        (
            "TECH_PLUS_INST_vs_PRESPECIFIED_T1",
            holdout["prob_tech_plus_inst"],
            holdout["prob_prespecified_t1"],
            "brier",
            None,
        ),
        (
            "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_plus_inst_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "precision",
            None,
        ),
        (
            "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_plus_inst_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "mean_net_return",
            returns,
        ),
        (
            "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_plus_inst_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "loss_rate",
            returns,
        ),
        (
            "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_plus_inst_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "tail_loss_rate",
            returns,
        ),
        (
            "TECH_BASE_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_base_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "precision",
            None,
        ),
        (
            "TECH_BASE_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_base_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "mean_net_return",
            returns,
        ),
        (
            "TECH_BASE_MATCHED_vs_PRESPECIFIED_T1",
            holdout["tech_base_matched_t1"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "tail_loss_rate",
            returns,
        ),
        (
            "TECH_PLUS_INST_MATCHED_vs_TECH_BASE_MATCHED",
            holdout["tech_plus_inst_matched_t1"].astype(float),
            holdout["tech_base_matched_t1"].astype(float),
            "precision",
            None,
        ),
        (
            "TECH_PLUS_INST_MATCHED_vs_TECH_BASE_MATCHED",
            holdout["tech_plus_inst_matched_t1"].astype(float),
            holdout["tech_base_matched_t1"].astype(float),
            "mean_net_return",
            returns,
        ),
        (
            "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1",
            holdout["tech_base_threshold"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "precision",
            None,
        ),
        (
            "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1",
            holdout["tech_base_threshold"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "mean_net_return",
            returns,
        ),
        (
            "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1",
            holdout["tech_base_threshold"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "loss_rate",
            returns,
        ),
        (
            "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1",
            holdout["tech_base_threshold"].astype(float),
            holdout["prespecified_t1"].astype(float),
            "tail_loss_rate",
            returns,
        ),
        (
            "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD",
            holdout["tech_plus_inst_threshold"].astype(float),
            holdout["tech_base_threshold"].astype(float),
            "precision",
            None,
        ),
        (
            "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD",
            holdout["tech_plus_inst_threshold"].astype(float),
            holdout["tech_base_threshold"].astype(float),
            "mean_net_return",
            returns,
        ),
        (
            "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD",
            holdout["tech_plus_inst_threshold"].astype(float),
            holdout["tech_base_threshold"].astype(float),
            "loss_rate",
            returns,
        ),
        (
            "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD",
            holdout["tech_plus_inst_threshold"].astype(float),
            holdout["tech_base_threshold"].astype(float),
            "tail_loss_rate",
            returns,
        ),
    ]
    records: list[dict[str, Any]] = []
    for offset, (comparison, challenger, baseline, metric, net_returns) in enumerate(
        comparisons
    ):
        result = date_block_bootstrap_paired_delta(
            dates,
            labels,
            challenger,
            baseline,
            metric=metric,
            n_bootstrap=repetitions,
            block_length=block_length,
            random_seed=seed + offset,
            threshold=0.5,
            tail_loss_threshold=float(
                config["analysis"]["tail_loss_net_return_pct"]
            ),
            net_returns=net_returns,
        )
        payload = asdict(result)
        payload.pop("samples", None)
        records.append(
            {"comparison": comparison, "evaluation_rows": len(holdout), **payload}
        )
    return pd.DataFrame(records)


def build_coefficient_table(
    models: dict[str, Any],
    *,
    technical_features: list[str],
    institutional_features: list[str],
) -> pd.DataFrame:
    """Return standardized coefficients for interpretation, not promotion."""

    institutional = set(institutional_features)
    records: list[dict[str, Any]] = []
    for variant, challenger in models.items():
        names = list(challenger.transform.feature_names)
        coefficients = np.asarray(
            challenger.logistic_model.coefficients, dtype=float
        )
        if len(names) != len(coefficients):
            raise AssertionError("model coefficient count does not match feature manifest")
        for feature, coefficient in zip(names, coefficients, strict=True):
            records.append(
                {
                    "variant": variant,
                    "feature": feature,
                    "family": "INSTITUTIONAL" if feature in institutional else "TECHNICAL",
                    "standardized_coefficient": float(coefficient),
                    "absolute_standardized_coefficient": abs(float(coefficient)),
                    "standardized_odds_ratio": float(np.exp(np.clip(coefficient, -20, 20))),
                    "selected_l2_penalty": float(
                        challenger.logistic_model.l2_penalty
                    ),
                }
            )
    return pd.DataFrame(records).sort_values(
        ["variant", "absolute_standardized_coefficient", "feature"],
        ascending=[True, False, True],
    )


def build_event_diagnostics(
    *,
    path: Path,
    factor_history: pd.DataFrame,
    models: dict[str, Any],
    technical_features: list[str],
    institutional_features: list[str],
    thresholds: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Project frozen full-market models over the D-10..D event trajectories."""

    trajectory = pd.read_csv(path, dtype={"stock_id": str})
    trajectory["stock_id"] = trajectory["stock_id"].astype(str).str.zfill(4)
    trajectory["observation_date"] = pd.to_datetime(
        trajectory["observation_date"], errors="raise"
    )
    trajectory["signal_date"] = pd.to_datetime(
        trajectory["signal_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    trajectory["event_id"] = (
        trajectory["signal_date"] + "|" + trajectory["stock_id"]
    )
    model_features = [*technical_features, *institutional_features]
    trajectory = trajectory.drop(
        columns=[column for column in model_features if column in trajectory],
        errors="ignore",
    )
    lookup_columns = [
        "observation_date",
        "stock_id",
        "technical_source_date",
        "institutional_source_date",
        "prespecified_t1_raw",
        *model_features,
    ]
    lookup_columns = list(dict.fromkeys(lookup_columns))
    lookup = factor_history[lookup_columns].copy()
    trajectory = trajectory.merge(
        lookup,
        on=["observation_date", "stock_id"],
        how="left",
        validate="many_to_one",
    )
    technical_source = pd.to_datetime(
        trajectory["technical_source_date"], errors="coerce"
    )
    institutional_source = pd.to_datetime(
        trajectory["institutional_source_date"], errors="coerce"
    )
    if (technical_source.notna() & technical_source.gt(trajectory["observation_date"])).any():
        raise AssertionError("event technical factor source is in the future")
    if (
        institutional_source.notna()
        & institutional_source.ge(trajectory["observation_date"])
    ).any():
        raise AssertionError("event institutional factor source is not strictly lagged")

    for variant, challenger in models.items():
        probability = predict_probability_challenger(challenger, trajectory)
        prefix = variant.lower()
        trajectory[f"prob_{prefix}"] = probability
        trajectory[f"alert_{prefix}"] = probability >= thresholds[variant]
    trajectory["alert_prespecified_t1"] = trajectory[
        "prespecified_t1_raw"
    ].fillna(False).astype(bool)
    profile_features = [
        *model_features,
        "prob_tech_base",
        "prob_tech_plus_inst",
    ]
    profile = build_event_factor_profile(
        trajectory,
        feature_columns=profile_features,
        return_column="d5_adjusted_return_pct",
    )
    alerts = _build_trajectory_alert_table(trajectory)
    forbidden = {
        "pre_margin_balance",
        "pre_foreign_net_shares_1d",
        "pre_foreign_net_shares_5d",
    }
    trajectory = trajectory.drop(columns=list(forbidden), errors="ignore")
    return trajectory, profile, alerts


def _build_trajectory_alert_table(trajectory: pd.DataFrame) -> pd.DataFrame:
    alert_columns = {
        "PRESPECIFIED_T1": "alert_prespecified_t1",
        "TECH_BASE": "alert_tech_base",
        "TECH_PLUS_INST": "alert_tech_plus_inst",
    }
    records: list[dict[str, Any]] = []
    for event_id, event in trajectory.groupby("event_id", sort=False):
        ordered = event.sort_values("lead_days", ascending=False)
        base = {
            "event_id": event_id,
            "signal_date": ordered["signal_date"].iloc[0],
            "stock_id": ordered["stock_id"].iloc[0],
            "stock_name": ordered["stock_name"].iloc[0]
            if "stock_name" in ordered
            else "",
            "d5_adjusted_return_pct": float(
                pd.to_numeric(ordered["d5_adjusted_return_pct"], errors="coerce").iloc[0]
            ),
        }
        for variant, column in alert_columns.items():
            matches = ordered.loc[ordered[column].fillna(False).astype(bool)]
            first = matches.iloc[0] if not matches.empty else None
            records.append(
                {
                    **base,
                    "variant": variant,
                    "alerted": first is not None,
                    "first_alert_lead_days": int(first["lead_days"])
                    if first is not None
                    else np.nan,
                    "first_alert_relative_day": str(first["relative_day"])
                    if first is not None
                    else "NO_ALERT",
                    "first_alert_observation_date": pd.Timestamp(
                        first["observation_date"]
                    ).strftime("%Y-%m-%d")
                    if first is not None
                    else "",
                }
            )
    return pd.DataFrame(records)


def build_ranked_holdout_candidates(
    rows: pd.DataFrame,
    *,
    sqlite_path: Path,
    finlab_root: Path,
    rules_csv: Path,
) -> pd.DataFrame:
    """Rank retrospective holdout selections with the frozen four-part score."""

    selected = rows.loc[
        rows["split"].eq("HOLDOUT")
        & rows["tech_plus_inst_matched_t1"].fillna(False).astype(bool)
        & ~rows["entry_locked_limit_up"].fillna(False).astype(bool)
    ].copy()
    if selected.empty:
        return pd.DataFrame()
    selected["asof_date"] = pd.to_datetime(selected["asof_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    scores = score_candidate_four_components(
        selected[["asof_date", "stock_id"]],
        sqlite_path=sqlite_path,
        finlab_root=finlab_root,
        rules_csv=rules_csv,
    )
    diagnostic_columns = [
        "asof_date",
        "stock_id",
        "prob_tech_base",
        "prob_tech_plus_inst",
        "prespecified_t1",
        "kd_confirmed_d",
        "net_return_pct",
        "target_gain_ge10",
        "target_gain_ge20",
        "kd_k9",
        "kd_spread",
        "rsi14",
        "close_to_ma20_pct",
        "ma20_slope_3d_pct_per_day",
        "volume_ratio_5",
        "volume_ratio_20",
        "volume_slope_5_pct_of_mean",
        "volume_slope_accel_5_pctpt",
        "institutional_total_net_volume_ratio_5d_pct",
        "institutional_total_net_volume_ratio_slope_5d_pctpt",
        "foreign_net_volume_ratio_5d_pct",
        "trust_net_volume_ratio_5d_pct",
    ]
    diagnostic_columns = [column for column in diagnostic_columns if column in selected]
    output = selected[diagnostic_columns].merge(
        scores,
        on=["asof_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    forbidden = [
        column
        for column in output
        if column == "pre_margin_balance"
        or column.endswith("_shares")
        or "foreign_net_shares" in column
    ]
    if forbidden:
        raise AssertionError(f"forbidden ranked output columns: {forbidden}")
    completeness = output["shadow_strength_complete"].fillna(False).astype(bool)
    output["_complete_sort"] = completeness.astype(int)
    output["_score_sort"] = pd.to_numeric(
        output["shadow_strength_score"], errors="coerce"
    ).fillna(-np.inf)
    output = output.sort_values(
        ["asof_date", "_complete_sort", "_score_sort", "prob_tech_plus_inst", "stock_id"],
        ascending=[True, False, False, False, True],
    ).drop(columns=["_complete_sort", "_score_sort"])
    return output.reset_index(drop=True)


def build_source_audit(
    sqlite_path: Path,
    *,
    signal_start: str,
    signal_end: str,
    modeling: pd.DataFrame,
) -> dict[str, Any]:
    """Record freshness, join coverage, and point-in-time source boundaries."""

    table_specs = {
        "daily_ohlcv_features": ("date", "stock_id"),
        "tw_institutional_flow_moving_averages_price_aligned_daily": (
            "date",
            "stock_id",
        ),
        "tw_adjusted_ohlcv_daily": ("date", "stock_id"),
        "tw_official_institutional_trading_daily": ("trade_date", "stock_id"),
        "stock_macd_indicators": ("date", "stock_id"),
        "stock_mtm10_ma10_indicators": ("date", "stock_id"),
    }
    tables: dict[str, Any] = {}
    with sqlite3.connect(sqlite_path) as connection:
        for table, (date_column, stock_column) in table_specs.items():
            row = connection.execute(
                f"""
                select min({date_column}), max({date_column}), count(*),
                       count(distinct {date_column} || '|' || {stock_column})
                from {table}
                """
            ).fetchone()
            h1_row = connection.execute(
                f"""
                select count(*), count(distinct {date_column} || '|' || {stock_column})
                from {table}
                where {date_column} between ? and ?
                """,
                [signal_start, signal_end],
            ).fetchone()
            tables[table] = {
                "minimum_date": row[0],
                "maximum_date": row[1],
                "all_rows": int(row[2]),
                "all_unique_stock_dates": int(row[3]),
                "analysis_rows": int(h1_row[0]),
                "analysis_unique_stock_dates": int(h1_row[1]),
            }
        flow_sources = pd.read_sql_query(
            """
            select flow_source, count(*) as rows
            from tw_institutional_flow_moving_averages_price_aligned_daily
            where date between ? and ?
            group by flow_source order by rows desc
            """,
            connection,
            params=[signal_start, signal_end],
        ).to_dict("records")
        adjusted_asof = connection.execute(
            """
            select min(asof_date), max(asof_date)
            from tw_adjusted_ohlcv_daily
            where date between ? and ?
            """,
            [signal_start, signal_end],
        ).fetchone()

    observation = pd.to_datetime(modeling["observation_date"], errors="raise")
    technical_source = pd.to_datetime(
        modeling["technical_source_date"], errors="coerce"
    )
    institutional_source = pd.to_datetime(
        modeling["institutional_source_date"], errors="coerce"
    )
    return {
        "sqlite_path": str(sqlite_path),
        "tables": tables,
        "analysis_flow_sources": flow_sources,
        "adjusted_label_data_asof_min": adjusted_asof[0],
        "adjusted_label_data_asof_max": adjusted_asof[1],
        "model_rows": int(len(modeling)),
        "technical_source_coverage": float(technical_source.notna().mean()),
        "institutional_source_coverage": float(institutional_source.notna().mean()),
        "technical_source_after_observation_violations": int(
            (technical_source.notna() & technical_source.gt(observation)).sum()
        ),
        "institutional_source_not_strictly_before_observation_violations": int(
            (institutional_source.notna() & institutional_source.ge(observation)).sum()
        ),
        "raw_foreign_share_features_used": False,
        "raw_margin_balance_features_used": False,
        "official_buy_sell_boundary": (
            "2026-05-26 onward only; excluded from primary model and retained as "
            "a future sensitivity source"
        ),
        "adjusted_price_role": "evaluator-only execution labels",
    }


def summarize_trajectory_alerts(alerts: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if alerts.empty:
        return records
    returns = pd.to_numeric(alerts["d5_adjusted_return_pct"], errors="coerce")
    alerts = alerts.assign(
        outcome_group=np.select(
            [returns.lt(0), returns.ge(10) & returns.lt(20), returns.ge(20)],
            ["D5_LOSS", "D5_GAIN_10_20", "D5_GAIN_GE20"],
            default="D5_0_10",
        )
    )
    for (variant, outcome), group in alerts.groupby(
        ["variant", "outcome_group"], sort=True
    ):
        alerted = group["alerted"].fillna(False).astype(bool)
        leads = pd.to_numeric(
            group.loc[alerted, "first_alert_lead_days"], errors="coerce"
        )
        records.append(
            {
                "variant": variant,
                "outcome_group": outcome,
                "events": int(len(group)),
                "alerted_events": int(alerted.sum()),
                "alert_rate": float(alerted.mean()),
                "median_first_alert_lead_days": float(leads.median())
                if len(leads)
                else np.nan,
            }
        )
    return records


def build_comparison_decision(
    *,
    probability_metrics: pd.DataFrame,
    decision_metrics: pd.DataFrame,
    monthly_metrics: pd.DataFrame,
    bootstrap: pd.DataFrame,
    minimum_rows: int,
    trajectory_alerts: pd.DataFrame | None = None,
    modeling_rows: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Apply a strict evidence gate without changing any formal strategy."""

    def probability(variant: str) -> pd.Series:
        match = probability_metrics[
            probability_metrics["split"].eq("HOLDOUT")
            & probability_metrics["variant"].eq(variant)
        ]
        if len(match) != 1:
            raise ValueError(f"missing HOLDOUT probability metric for {variant}")
        return match.iloc[0]

    def decision(variant: str) -> pd.Series:
        preferred = decision_metrics[
            decision_metrics["split"].eq("HOLDOUT")
            & decision_metrics["variant"].eq(variant)
            & decision_metrics["view"].eq("TRADABLE")
        ]
        if preferred.empty:
            preferred = decision_metrics[
                decision_metrics["split"].eq("HOLDOUT")
                & decision_metrics["variant"].eq(variant)
                & decision_metrics["view"].eq("PRIMARY")
            ]
        if len(preferred) != 1:
            raise ValueError(f"missing HOLDOUT decision metric for {variant}")
        return preferred.iloc[0]

    def boot(comparison: str, metric: str) -> pd.Series:
        match = bootstrap[
            bootstrap["comparison"].eq(comparison)
            & bootstrap["metric"].eq(metric)
        ]
        if len(match) != 1:
            raise ValueError(f"missing bootstrap {comparison}/{metric}")
        return match.iloc[0]

    tech_probability = probability("TECH_BASE")
    inst_probability = probability("TECH_PLUS_INST")
    t1_probability = probability("PRESPECIFIED_T1")
    t1 = decision("PRESPECIFIED_T1")
    tech = decision("TECH_BASE_MATCHED_T1")
    inst = decision("TECH_PLUS_INST_MATCHED_T1")
    tech_selective = decision("TECH_BASE_THRESHOLD")
    inst_selective = decision("TECH_PLUS_INST_THRESHOLD")
    precision_vs_t1 = boot(
        "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1", "precision"
    )
    return_vs_t1 = boot(
        "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1", "mean_net_return"
    )
    tail_vs_t1 = boot(
        "TECH_PLUS_INST_MATCHED_vs_PRESPECIFIED_T1", "tail_loss_rate"
    )
    tech_precision_vs_t1 = boot(
        "TECH_BASE_MATCHED_vs_PRESPECIFIED_T1", "precision"
    )
    tech_return_vs_t1 = boot(
        "TECH_BASE_MATCHED_vs_PRESPECIFIED_T1", "mean_net_return"
    )
    tech_tail_vs_t1 = boot(
        "TECH_BASE_MATCHED_vs_PRESPECIFIED_T1", "tail_loss_rate"
    )
    brier_vs_tech = boot("TECH_PLUS_INST_vs_TECH_BASE", "brier")
    precision_vs_tech = boot(
        "TECH_PLUS_INST_MATCHED_vs_TECH_BASE_MATCHED", "precision"
    )
    return_vs_tech = boot(
        "TECH_PLUS_INST_MATCHED_vs_TECH_BASE_MATCHED", "mean_net_return"
    )
    selective_precision_vs_t1 = boot(
        "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1", "precision"
    )
    selective_return_vs_t1 = boot(
        "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1", "mean_net_return"
    )
    selective_loss_vs_t1 = boot(
        "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1", "loss_rate"
    )
    selective_tail_vs_t1 = boot(
        "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1", "tail_loss_rate"
    )
    selective_inst_precision_vs_tech = boot(
        "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD", "precision"
    )
    selective_inst_return_vs_tech = boot(
        "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD", "mean_net_return"
    )

    monthly = monthly_metrics[
        monthly_metrics["split"].eq("HOLDOUT")
        & monthly_metrics["variant"].isin(
            [
                "PRESPECIFIED_T1",
                "TECH_BASE_MATCHED_T1",
                "TECH_PLUS_INST_MATCHED_T1",
            ]
        )
    ]
    monthly_pivot = monthly.pivot(
        index="month", columns="variant", values="precision_gain_ge10"
    )
    stable_months = (
        monthly_pivot.get("TECH_PLUS_INST_MATCHED_T1", pd.Series(dtype=float))
        >= monthly_pivot.get("PRESPECIFIED_T1", pd.Series(dtype=float))
    )
    monthly_non_worse = bool(len(stable_months) >= 2 and stable_months.all())
    technical_stable_months = (
        monthly_pivot.get("TECH_BASE_MATCHED_T1", pd.Series(dtype=float))
        >= monthly_pivot.get("PRESPECIFIED_T1", pd.Series(dtype=float))
    )
    technical_monthly_non_worse = bool(
        len(technical_stable_months) >= 2 and technical_stable_months.all()
    )
    selective_monthly = monthly_metrics[
        monthly_metrics["split"].eq("HOLDOUT")
        & monthly_metrics["variant"].isin(
            ["PRESPECIFIED_T1", "TECH_BASE_THRESHOLD"]
        )
    ].pivot(index="month", columns="variant", values="precision_gain_ge10")
    selective_stable_months = (
        selective_monthly.get("TECH_BASE_THRESHOLD", pd.Series(dtype=float))
        >= selective_monthly.get("PRESPECIFIED_T1", pd.Series(dtype=float))
    )
    selective_monthly_non_worse = bool(
        len(selective_stable_months) >= 2 and selective_stable_months.all()
    )
    gates_vs_t1 = {
        "minimum_selected_rows": int(inst["selected_rows"]) >= minimum_rows,
        "higher_holdout_precision": float(inst["precision_gain_ge10"])
        > float(t1["precision_gain_ge10"]),
        "higher_holdout_mean_net_return": float(inst["mean_net_return_pct"])
        > float(t1["mean_net_return_pct"]),
        "non_worse_holdout_loss_rate": float(inst["loss_rate"])
        <= float(t1["loss_rate"]),
        "non_worse_holdout_tail_loss_rate": float(inst["tail_loss_rate"])
        <= float(t1["tail_loss_rate"]),
        "precision_bootstrap_ci_above_zero": float(
            precision_vs_t1["confidence_lower"]
        )
        > 0.0,
        "return_bootstrap_ci_above_zero": float(return_vs_t1["confidence_lower"])
        > 0.0,
        "tail_loss_bootstrap_ci_at_or_below_zero": float(
            tail_vs_t1["confidence_upper"]
        )
        <= 0.0,
        "both_holdout_months_non_worse_precision": monthly_non_worse,
    }
    gates_tech_vs_t1 = {
        "minimum_selected_rows": int(tech["selected_rows"]) >= minimum_rows,
        "higher_holdout_precision": float(tech["precision_gain_ge10"])
        > float(t1["precision_gain_ge10"]),
        "higher_holdout_mean_net_return": float(tech["mean_net_return_pct"])
        > float(t1["mean_net_return_pct"]),
        "non_worse_holdout_loss_rate": float(tech["loss_rate"])
        <= float(t1["loss_rate"]),
        "non_worse_holdout_tail_loss_rate": float(tech["tail_loss_rate"])
        <= float(t1["tail_loss_rate"]),
        "precision_bootstrap_ci_above_zero": float(
            tech_precision_vs_t1["confidence_lower"]
        )
        > 0.0,
        "return_bootstrap_ci_above_zero": float(
            tech_return_vs_t1["confidence_lower"]
        )
        > 0.0,
        "tail_loss_bootstrap_ci_at_or_below_zero": float(
            tech_tail_vs_t1["confidence_upper"]
        )
        <= 0.0,
        "both_holdout_months_non_worse_precision": technical_monthly_non_worse,
    }
    gates_inst_increment = {
        "lower_holdout_brier": float(inst_probability["brier"])
        < float(tech_probability["brier"]),
        "lower_holdout_logloss": float(inst_probability["logloss"])
        < float(tech_probability["logloss"]),
        "brier_bootstrap_ci_below_zero": float(brier_vs_tech["confidence_upper"])
        < 0.0,
        "higher_equal_coverage_precision": float(inst["precision_gain_ge10"])
        > float(tech["precision_gain_ge10"]),
        "higher_equal_coverage_return": float(inst["mean_net_return_pct"])
        > float(tech["mean_net_return_pct"]),
        "precision_bootstrap_ci_above_zero": float(
            precision_vs_tech["confidence_lower"]
        )
        > 0.0,
        "return_bootstrap_ci_above_zero": float(return_vs_tech["confidence_lower"])
        > 0.0,
    }
    gates_selective_tech_vs_t1 = {
        "minimum_selected_rows": int(tech_selective["selected_rows"])
        >= minimum_rows,
        "higher_holdout_precision": float(tech_selective["precision_gain_ge10"])
        > float(t1["precision_gain_ge10"]),
        "higher_holdout_mean_net_return": float(
            tech_selective["mean_net_return_pct"]
        )
        > float(t1["mean_net_return_pct"]),
        "non_worse_holdout_loss_rate": float(tech_selective["loss_rate"])
        <= float(t1["loss_rate"]),
        "non_worse_holdout_tail_loss_rate": float(tech_selective["tail_loss_rate"])
        <= float(t1["tail_loss_rate"]),
        "precision_bootstrap_ci_above_zero": float(
            selective_precision_vs_t1["confidence_lower"]
        )
        > 0.0,
        "return_bootstrap_ci_above_zero": float(
            selective_return_vs_t1["confidence_lower"]
        )
        > 0.0,
        "loss_bootstrap_ci_below_zero": float(
            selective_loss_vs_t1["confidence_upper"]
        )
        < 0.0,
        "both_holdout_months_non_worse_precision": selective_monthly_non_worse,
    }
    beats_t1 = bool(all(gates_vs_t1.values()))
    tech_beats_t1 = bool(all(gates_tech_vs_t1.values()))
    institution_adds = bool(all(gates_inst_increment.values()))
    selective_tech_edge = bool(all(gates_selective_tech_vs_t1.values()))
    selective_tail_confirmed = bool(
        float(selective_tail_vs_t1["confidence_upper"]) <= 0.0
    )
    selective_concentration: dict[str, Any] = {}
    if modeling_rows is not None and not modeling_rows.empty:
        selective_rows = modeling_rows.loc[
            modeling_rows["split"].eq("HOLDOUT")
            & modeling_rows["tech_base_threshold"].fillna(False).astype(bool)
            & ~modeling_rows["entry_locked_limit_up"].fillna(False).astype(bool)
        ].copy()
        daily_counts = (
            selective_rows.groupby("asof_date", as_index=False)
            .size()
            .sort_values(["size", "asof_date"], ascending=[False, True])
        )
        top_two = daily_counts.head(2)
        selective_concentration = {
            "tradable_selected_rows": int(len(selective_rows)),
            "selected_dates": int(daily_counts["asof_date"].nunique()),
            "largest_daily_count": int(daily_counts["size"].max())
            if not daily_counts.empty
            else 0,
            "top_two_dates": [
                {
                    "asof_date": str(row.asof_date),
                    "selected_rows": int(row.size),
                }
                for row in top_two.itertuples(index=False)
            ],
            "top_two_dates_share": float(top_two["size"].sum() / len(selective_rows))
            if len(selective_rows)
            else 0.0,
        }
    conclusion = (
        "每天補足與現行 T-1 相同數量時，技術版雖提高 +10% 命中率，尾損卻變差，"
        "不能全面取代目前策略。若允許沒有把握就不發訊號，純技術高信心門檻版在"
        " 5～6 月的命中、平均淨報酬與虧損率均有統計改善，可列為選擇性影子候選；"
        "但尾損改善仍未確認，優勢集中在少數強勢日期，而且這是在已檢視 holdout 後才注意到的版本；"
        "只能稱為回溯型影子候選，須等待 2026-07-14 之後前向驗證。"
        if selective_tech_edge
        else (
            "技術版提高了 +10% 命中率，但尾損率變差且報酬改善沒有統計把握；"
            "加入法人量後命中與平均淨報酬又略降。尚不能稱為比目前 T-1 影子策略更好，先維持原策略。"
        )
    )
    return {
        "retrospective_holdout_beats_current_t1": beats_t1 or tech_beats_t1,
        "full_daily_quota_replacement_beats_current_t1": beats_t1
        or tech_beats_t1,
        "technical_only_beats_current_t1": tech_beats_t1,
        "selective_technical_threshold_historical_edge": selective_tech_edge,
        "selective_threshold_tail_improvement_confirmed": selective_tail_confirmed,
        "selective_threshold_live_deployable": False,
        "selective_threshold_post_selection_warning": True,
        "selective_threshold_concentration": selective_concentration,
        "institutional_ratios_add_incremental_value": institution_adds,
        "gates_tech_plus_inst_vs_current_t1": gates_vs_t1,
        "gates_technical_only_vs_current_t1": gates_tech_vs_t1,
        "gates_selective_technical_threshold_vs_current_t1": (
            gates_selective_tech_vs_t1
        ),
        "gates_institutional_increment": gates_inst_increment,
        "holdout_deltas": {
            "precision_vs_t1_pctpt": (
                float(inst["precision_gain_ge10"])
                - float(t1["precision_gain_ge10"])
            )
            * 100.0,
            "mean_net_return_vs_t1_pctpt": float(inst["mean_net_return_pct"])
            - float(t1["mean_net_return_pct"]),
            "loss_rate_vs_t1_pctpt": (
                float(inst["loss_rate"]) - float(t1["loss_rate"])
            )
            * 100.0,
            "brier_vs_tech": float(inst_probability["brier"])
            - float(tech_probability["brier"]),
            "logloss_vs_tech": float(inst_probability["logloss"])
            - float(tech_probability["logloss"]),
            "brier_vs_t1": float(inst_probability["brier"])
            - float(t1_probability["brier"]),
            "technical_precision_vs_t1_pctpt": (
                float(tech["precision_gain_ge10"])
                - float(t1["precision_gain_ge10"])
            )
            * 100.0,
            "technical_mean_net_return_vs_t1_pctpt": float(
                tech["mean_net_return_pct"]
            )
            - float(t1["mean_net_return_pct"]),
            "technical_tail_loss_vs_t1_pctpt": (
                float(tech["tail_loss_rate"]) - float(t1["tail_loss_rate"])
            )
            * 100.0,
            "selective_technical_precision_vs_t1_pctpt": (
                float(tech_selective["precision_gain_ge10"])
                - float(t1["precision_gain_ge10"])
            )
            * 100.0,
            "selective_technical_mean_net_return_vs_t1_pctpt": float(
                tech_selective["mean_net_return_pct"]
            )
            - float(t1["mean_net_return_pct"]),
            "selective_technical_loss_rate_vs_t1_pctpt": (
                float(tech_selective["loss_rate"]) - float(t1["loss_rate"])
            )
            * 100.0,
            "selective_technical_tail_loss_vs_t1_pctpt": (
                float(tech_selective["tail_loss_rate"])
                - float(t1["tail_loss_rate"])
            )
            * 100.0,
            "selective_inst_precision_vs_tech_pctpt": float(
                inst_selective["precision_gain_ge10"]
                - tech_selective["precision_gain_ge10"]
            )
            * 100.0,
            "selective_inst_return_vs_tech_pctpt": float(
                inst_selective["mean_net_return_pct"]
                - tech_selective["mean_net_return_pct"]
            ),
            "selective_inst_precision_bootstrap_ci": [
                float(selective_inst_precision_vs_tech["confidence_lower"]),
                float(selective_inst_precision_vs_tech["confidence_upper"]),
            ],
            "selective_inst_return_bootstrap_ci": [
                float(selective_inst_return_vs_tech["confidence_lower"]),
                float(selective_inst_return_vs_tech["confidence_upper"]),
            ],
        },
        "trajectory_alert_summary": summarize_trajectory_alerts(
            trajectory_alerts if trajectory_alerts is not None else pd.DataFrame()
        ),
        "plain_language_conclusion": conclusion,
        "mode": MODE,
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "live_deployable": False,
    }


def write_outputs(result: dict[str, Any], *, output_dir: Path) -> None:
    """Persist compact evidence tables, the full factor panel, and the report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = "zhu_walkline_d10_deep_factor"
    csv_outputs = {
        "split_audit": f"{prefix}_split_audit.csv",
        "probability_metrics": f"{prefix}_probability_metrics.csv",
        "decision_metrics": f"{prefix}_decision_metrics.csv",
        "monthly_metrics": f"{prefix}_monthly_metrics.csv",
        "bootstrap": f"{prefix}_bootstrap.csv",
        "coefficients": f"{prefix}_coefficients.csv",
        "factor_frontier": f"{prefix}_frontier.csv",
        "factor_frontier_splits": f"{prefix}_frontier_splits.csv",
        "volume_thresholds": f"{prefix}_volume_thresholds.csv",
        "trajectory": f"{prefix}_trajectory_rows.csv",
        "trajectory_profile": f"{prefix}_trajectory_profile.csv",
        "trajectory_alerts": f"{prefix}_trajectory_alerts.csv",
        "selected_rows": f"{prefix}_ranked_holdout_candidates.csv",
        "operational_selection_audit": f"{prefix}_operational_selection_audit.csv",
    }
    artifacts: dict[str, str] = {}
    for key, filename in csv_outputs.items():
        path = output_dir / filename
        frame = result[key].replace([np.inf, -np.inf], np.nan)
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        artifacts[key] = str(path)
    model_path = output_dir / f"{prefix}_full_market_modeling_rows.parquet"
    result["modeling_rows"].replace([np.inf, -np.inf], np.nan).to_parquet(
        model_path, index=False
    )
    artifacts["modeling_rows"] = str(model_path)

    report_path = output_dir / f"{prefix}_report.md"
    summary_path = output_dir / f"{prefix}_summary.json"
    artifacts["report"] = str(report_path)
    artifacts["summary"] = str(summary_path)
    result["summary"]["artifacts"] = artifacts
    report_path.write_text(render_markdown_report(result), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            _json_safe(result["summary"]),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def refresh_evaluation_outputs(
    *, config: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    """Refresh bootstrap/comparison evidence without rebuilding frozen factors."""

    started = perf_counter()
    prefix = "zhu_walkline_d10_deep_factor"
    required = {
        "modeling_rows": output_dir / f"{prefix}_full_market_modeling_rows.parquet",
        "decision_metrics": output_dir / f"{prefix}_decision_metrics.csv",
        "probability_metrics": output_dir / f"{prefix}_probability_metrics.csv",
        "monthly_metrics": output_dir / f"{prefix}_monthly_metrics.csv",
        "factor_frontier": output_dir / f"{prefix}_frontier.csv",
        "factor_frontier_splits": output_dir / f"{prefix}_frontier_splits.csv",
        "volume_thresholds": output_dir / f"{prefix}_volume_thresholds.csv",
        "trajectory_alerts": output_dir / f"{prefix}_trajectory_alerts.csv",
        "operational_selection_audit": output_dir
        / f"{prefix}_operational_selection_audit.csv",
        "summary": output_dir / f"{prefix}_summary.json",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("evaluation refresh missing artifacts: " + ", ".join(missing))
    modeling = pd.read_parquet(required["modeling_rows"])
    result: dict[str, Any] = {
        key: pd.read_csv(path)
        for key, path in required.items()
        if key not in {"modeling_rows", "summary"}
    }
    result["bootstrap"] = build_holdout_bootstrap(modeling, config=config)
    result["summary"] = json.loads(required["summary"].read_text(encoding="utf-8"))
    result["summary"]["comparison"] = build_comparison_decision(
        probability_metrics=result["probability_metrics"],
        decision_metrics=result["decision_metrics"],
        monthly_metrics=result["monthly_metrics"],
        bootstrap=result["bootstrap"],
        minimum_rows=int(config["factor_frontier"]["minimum_selected_rows_per_split"]),
        trajectory_alerts=result["trajectory_alerts"],
        modeling_rows=modeling,
    )
    result["summary"]["evaluation_refresh"] = {
        "source_modeling_rows": str(required["modeling_rows"]),
        "source_rows": int(len(modeling)),
        "bootstrap_block_length_days": int(
            config["factor_frontier"].get("bootstrap_block_length_days", 5)
        ),
        "tail_loss_threshold_pct": float(
            config["analysis"]["tail_loss_net_return_pct"]
        ),
        "elapsed_seconds": perf_counter() - started,
    }
    result["bootstrap"].replace([np.inf, -np.inf], np.nan).to_csv(
        output_dir / f"{prefix}_bootstrap.csv", index=False, encoding="utf-8-sig"
    )
    (output_dir / f"{prefix}_report.md").write_text(
        render_markdown_report(result), encoding="utf-8"
    )
    required["summary"].write_text(
        json.dumps(
            _json_safe(result["summary"]),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def render_markdown_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    comparison = summary["comparison"]
    selective_concentration = comparison.get(
        "selective_threshold_concentration", {}
    )
    decisions = result["decision_metrics"]
    holdout_decisions = decisions[
        decisions["split"].eq("HOLDOUT")
        & decisions["view"].eq("TRADABLE")
        & decisions["variant"].isin(
            [
                "ALL_ELIGIBLE",
                "PRESPECIFIED_T1",
                "D10_FIXED_6",
                "KD_CONFIRMED_D",
                "TECH_BASE_MATCHED_T1",
                "TECH_PLUS_INST_MATCHED_T1",
            ]
        )
    ]
    if holdout_decisions.empty:
        holdout_decisions = decisions[
            decisions["split"].eq("HOLDOUT")
            & decisions["view"].eq("PRIMARY")
        ]
    holdout_selective = decisions[
        decisions["split"].eq("HOLDOUT")
        & decisions["view"].eq("TRADABLE")
        & decisions["variant"].isin(
            [
                "PRESPECIFIED_T1",
                "TECH_BASE_THRESHOLD",
                "TECH_PLUS_INST_THRESHOLD",
            ]
        )
    ]
    probability = result["probability_metrics"]
    holdout_probability = probability[
        probability["split"].eq("HOLDOUT")
        & probability["variant"].isin(
            ["PRESPECIFIED_T1", "TECH_BASE", "TECH_PLUS_INST"]
        )
    ]
    monthly = result["monthly_metrics"]
    holdout_monthly = monthly[
        monthly["split"].eq("HOLDOUT")
        & monthly["variant"].isin(
            [
                "PRESPECIFIED_T1",
                "TECH_BASE_MATCHED_T1",
                "TECH_PLUS_INST_MATCHED_T1",
                "TECH_BASE_THRESHOLD",
                "TECH_PLUS_INST_THRESHOLD",
            ]
        )
    ]
    selective_bootstrap = result["bootstrap"][
        result["bootstrap"]["comparison"].isin(
            [
                "TECH_BASE_THRESHOLD_vs_PRESPECIFIED_T1",
                "TECH_PLUS_INST_THRESHOLD_vs_TECH_BASE_THRESHOLD",
            ]
        )
    ]
    frontier = result["factor_frontier"]
    frontier_splits = result["factor_frontier_splits"]
    top_frontier = frontier.head(15).merge(
        frontier_splits[frontier_splits["split"].eq("HOLDOUT")][
            [
                "feature",
                "selected_rows",
                "selected_gain_rate",
                "precision_lift_vs_split",
                "selected_mean_return_pct",
            ]
        ],
        on="feature",
        how="left",
        suffixes=("_discovery", "_holdout"),
    )
    volume = result["volume_thresholds"]
    volume_excerpt = volume[
        volume["split"].eq("HOLDOUT")
        & volume["threshold"].isin([0.5, 0.6, 0.7, 0.75, 0.8, 1.0, 1.2])
    ]
    trajectory = pd.DataFrame(comparison["trajectory_alert_summary"])
    source_tables = pd.DataFrame(
        [
            {"table": table, **details}
            for table, details in summary["source_audit"]["tables"].items()
        ]
    )
    operational = (
        result["operational_selection_audit"]
        .groupby("variant", as_index=False)
        .agg(
            trading_days=("asof_date", "nunique"),
            reference_quota=("reference_quota", "sum"),
            selected_rows=("selected_rows", "sum"),
            quota_shortfall=("quota_shortfall", "sum"),
        )
    )
    significant_bh = int(
        pd.to_numeric(frontier.get("bh_q_value"), errors="coerce").le(0.05).sum()
    )
    significant_fwer = int(
        pd.to_numeric(frontier.get("max_t_fwer_p_value"), errors="coerce")
        .le(0.05)
        .sum()
    )
    lines = [
        "# Zhu Walkline D-10～D 深層因子影子研究",
        "",
        "## 結論",
        "",
        comparison["plain_language_conclusion"],
        "",
        f"- 分析區間：{summary['as_of']} 截止；訊號樣本為 2026-01～2026-06。",
        f"- 全市場可評估列：{summary['eligible_model_rows']:,}；技術因子 {summary['technical_feature_count']} 項、嚴格落後法人量因子 {summary['institutional_feature_count']} 項。",
        f"- 個別因子多重檢定：BH q≤0.05 有 {significant_bh} 項；max-T FWER≤0.05 有 {significant_fwer} 項。",
        "- 個別因子置換只保留同日市場環境，未完整保留個股、產業與重疊 D+5 群聚；顯著數只能用來排研究優先順序，不能單獨證明可交易優勢。",
        f"- 每日等配額全面取代現行 T-1：{comparison['full_daily_quota_replacement_beats_current_t1']}。",
        f"- 可棄權的純技術高信心門檻具歷史留出優勢：{comparison['selective_technical_threshold_historical_edge']}。",
        f"- 高信心門檻的尾損改善已確認：{comparison['selective_threshold_tail_improvement_confirmed']}。",
        f"- 法人量比例有穩定增益：{comparison['institutional_ratios_add_incremental_value']}。",
        "- 本報告不是交易建議；2026H1 已被反覆檢視，結果不可視為全新前向樣本。",
        "",
        "## 鎖定保留樣本：同日 T-1 配額與同股冷卻比較",
        "",
        _markdown_table(
            holdout_decisions,
            [
                "variant",
                "selected_rows",
                "precision_gain_ge10",
                "precision_lift_vs_split",
                "gain_ge20_rate",
                "loss_rate",
                "tail_loss_rate",
                "mean_net_return_pct",
                "median_net_return_pct",
            ],
        ),
        "",
        "`TECH_*_MATCHED_T1` 在完整、無標籤的候選母體逐日依機率排序，先排除同股 5 交易日冷卻中的股票，再補足現行 T-1 當日配額；次日鎖漲停無法成交者另由 tradable view 排除。",
        "",
        _markdown_table(
            operational,
            [
                "variant",
                "trading_days",
                "reference_quota",
                "selected_rows",
                "quota_shortfall",
            ],
        ),
        "",
        "## 可棄權的高信心門檻版",
        "",
        "門檻只用 3 月驗證集的現行 T-1 總訊號數決定，沒有用 5～6 月結果挑門檻；模型允許低信心時不發訊號，因此這是少量影子候選，不是每日等配額替代品。",
        "",
        _markdown_table(
            holdout_selective,
            [
                "variant",
                "selected_rows",
                "precision_gain_ge10",
                "gain_ge20_rate",
                "loss_rate",
                "tail_loss_rate",
                "mean_net_return_pct",
                "median_net_return_pct",
                "selected_dates",
                "empty_dates",
            ],
        ),
        "",
        "模型整體機率校準仍不如簡單基準，所以這個門檻目前只能解讀為凍結分數切點，不能把 0.20 當成真的 20% 上漲機率。",
        f"高信心訊號最多單日 {selective_concentration.get('largest_daily_count', 0)} 檔；最多的兩個日期合計占 {selective_concentration.get('top_two_dates_share', 0.0):.1%}。這表示結果高度受強勢市場日期影響，尚未通過資金容量與每日上限測試。",
        "這個門檻版是在研究者已看過 2026H1 holdout 後才被提升為重點，因此下列 bootstrap 只能描述這段歷史的不確定性，不能消除事後選模偏誤。",
        "",
        _markdown_table(
            selective_bootstrap,
            [
                "comparison",
                "metric",
                "observed_delta",
                "confidence_lower",
                "confidence_upper",
                "two_sided_p_value",
                "block_length",
                "tail_loss_threshold",
            ],
            max_rows=20,
        ),
        "",
        "## 機率品質",
        "",
        _markdown_table(
            holdout_probability,
            [
                "variant",
                "observation_count",
                "brier",
                "logloss",
                "ece",
                "precision",
                "lift",
            ],
        ),
        "",
        "## 5 月／6 月穩定性",
        "",
        _markdown_table(
            holdout_monthly,
            [
                "month",
                "variant",
                "selected_rows",
                "precision_gain_ge10",
                "loss_rate",
                "mean_net_return_pct",
            ],
        ),
        "",
        "## D-10～D 因子前緣",
        "",
        "門檻與方向只用 1～2 月 discovery 決定，再原封不動套到後續月份。",
        "",
        _markdown_table(
            top_frontier,
            [
                "feature",
                "direction",
                "threshold",
                "standardized_effect",
                "permutation_p_value",
                "bh_q_value",
                "max_t_fwer_p_value",
                "selected_rows_holdout",
                "selected_gain_rate",
                "precision_lift_vs_split",
                "selected_mean_return_pct",
            ],
        ),
        "",
        "## 成交量門檻敏感度",
        "",
        "下表只是事前列出的固定門檻敏感度，不從 5～6 月挑贏家。量的原始股數不可跨股票比較，因此以個股 rolling 量比與斜率百分比為主。",
        "",
        _markdown_table(
            volume_excerpt,
            [
                "feature",
                "direction",
                "threshold",
                "selected_rows",
                "selected_gain_rate",
                "precision_lift_vs_split",
                "selected_loss_rate",
                "selected_mean_return_pct",
            ],
            max_rows=30,
        ),
        "",
        "## 已確認事件內的提早天數診斷",
        "",
        "這一段只回答『在最後會確認的事件中能提早幾天』，不能拿來估全市場誤報率；全市場比較以上面的 holdout 為準。",
        "",
        _markdown_table(
            trajectory,
            [
                "variant",
                "outcome_group",
                "events",
                "alerted_events",
                "alert_rate",
                "median_first_alert_lead_days",
            ],
            max_rows=30,
        ),
        "",
        "## 資料與無前視稽核",
        "",
        _markdown_table(
            source_tables,
            [
                "table",
                "minimum_date",
                "maximum_date",
                "analysis_rows",
                "analysis_unique_stock_dates",
            ],
        ),
        "",
        f"- 技術來源晚於觀察日違規：{summary['source_audit']['technical_source_after_observation_violations']}。",
        f"- 法人來源未嚴格早於觀察日違規：{summary['source_audit']['institutional_source_not_strictly_before_observation_violations']}。",
        "- 法人只用前一可得日的淨買賣量／個股成交量比例、正值日比例、斜率與斜率變化；不使用原始外資股數。",
        "- 融資原始餘額不進模型；既有五日融資變化只留在四項影子強度報告排序。",
        "- 調整價只用於次日開盤進場與第五日收盤標籤；企業行動橫跨期間列排除於主評估。",
        "",
        "## 四項影子強度",
        "",
        "最終候選仍只依『主力、無上影、量比、融資五日變化』四項顯示強度；模型機率是研究欄位，不能取代正式策略。缺項一律標示 `INSUFFICIENT_FEATURES`／不完整狀態，不補零。",
        "",
        "## 執行與治理",
        "",
        f"- 成本：雙邊手續費各 {summary['cost_assumptions']['brokerage_fee_rate_each_side']:.6f}、賣出稅 {summary['cost_assumptions']['sell_tax_rate']:.6f}、雙邊滑價各 {summary['cost_assumptions']['one_way_slippage_rate']:.6f}。",
        f"- mode={summary['mode']}",
        "- formal_champion_changed=False",
        "- formal_trade_effect=False",
        "- no formal strategy modified",
        f"- next_required_gate={summary['next_required_gate']}",
        f"- promotion_decision={summary['promotion_decision']}",
        "",
        "## 白話文",
        "",
        comparison["plain_language_conclusion"],
        "這次不是只看幾檔成功股票，而是把全市場每個可交易日都放進同一把尺；如果加入很多指標只是讓舊資料看起來更漂亮、但 5～6 月沒有穩定勝出，就不把它升級。",
        "",
    ]
    return "\n".join(lines)


def _markdown_table(
    frame: pd.DataFrame, columns: list[str], *, max_rows: int = 50
) -> str:
    available = [column for column in columns if column in frame]
    if frame.empty or not available:
        return "_無可用資料_"
    shown = frame[available].head(max_rows)
    header = "| " + " | ".join(available) + " |"
    separator = "|" + "|".join(["---"] * len(available)) + "|"
    body = []
    for row in shown.itertuples(index=False, name=None):
        values = [str(_format_scalar(value)).replace("|", "\\|") for value in row]
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def _format_scalar(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    if isinstance(value, (bool, np.bool_)):
        return "True" if value else "False"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.6f}"
    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if value is pd.NA or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("configuration root must be a mapping")
    if payload.get("mode") != MODE or payload.get("formal_trade_effect") is not False:
        raise ValueError("deep-factor research must remain shadow-only")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "config" / "zhu_walkline_d10_deep_factor_research.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT
        / "reports"
        / "zhu_walkline_d10_deep_factor_research_2026_01_06",
    )
    parser.add_argument(
        "--refresh-evaluation-only",
        action="store_true",
        help="reuse frozen full-market rows and refresh bootstrap/report only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config.resolve())
    output_dir = args.output_dir.resolve()
    result = (
        refresh_evaluation_outputs(config=config, output_dir=output_dir)
        if args.refresh_evaluation_only
        else run_research(config=config, output_dir=output_dir)
    )
    summary = result["summary"]
    print(f"mode={summary['mode']}")
    print(f"formal_champion_changed={summary['formal_champion_changed']}")
    print(f"formal_trade_effect={summary['formal_trade_effect']}")
    print(f"report={summary['artifacts']['report']}")
    print(summary["comparison"]["plain_language_conclusion"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
