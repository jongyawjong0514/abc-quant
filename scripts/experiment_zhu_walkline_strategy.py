"""Compare Zhu walkline shadow strategy variants with execution-aware labels.

The experiment keeps the existing scanner and driver score unchanged. Variant
membership uses only signal-date fields. Adjusted next-open entry, D+20 close,
costs, and corporate-action fields are evaluator-only labels attached after the
screen is formed.
"""

from __future__ import annotations

import argparse
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

from scripts.backtest_zhu_walkline_driver_screen import (  # noqa: E402
    build_same_count_baselines,
    score_driver_screen,
)


MODE = "shadow_observation_only"
BASELINE_VARIANT = "BASELINE_SCORE_11"
EVALUATION_SCOPE = "cooldown_20d"

DAILY_FEATURE_COLUMNS = [
    "date",
    "stock_id",
    "open_to_close_pct",
    "gap_up_pct",
    "close_from_high_pct",
    "close_location_in_bar",
    "sma5",
    "sma10",
    "sma20",
    "sma60",
    "volume",
    "volume_ma20",
    "day_volume_ratio_20",
    "intraday_return_rankpct",
    "range_pos_20_rankpct",
    "close_from_high_rankpct",
    "upper_tail_flag",
    "volume_exhaustion_flag",
    "late_chase_risk_flag",
]

VARIANT_SPECS = [
    {
        "variant": BASELINE_VARIANT,
        "cohort_type": "baseline",
        "rule": "driver_score >= 11",
    },
    {
        "variant": "SCORE_12",
        "cohort_type": "mutation",
        "rule": "driver_score >= 12",
    },
    {
        "variant": "BASELINE_NO_LATE_CHASE",
        "cohort_type": "mutation",
        "rule": "driver_score >= 11 and late_chase_risk_flag == 0",
    },
    {
        "variant": "BASELINE_NO_UPPER_TAIL",
        "cohort_type": "mutation",
        "rule": "driver_score >= 11 and upper_tail_flag == 0",
    },
    {
        "variant": "BASELINE_NO_VOLUME_EXHAUSTION",
        "cohort_type": "mutation",
        "rule": "driver_score >= 11 and volume_exhaustion_flag == 0",
    },
    {
        "variant": "BASELINE_MA5_GAP_CAP_12",
        "cohort_type": "mutation",
        "rule": "driver_score >= 11 and close_to_sma5_pct <= 12",
    },
    {
        "variant": "BASELINE_LIQUIDITY_20M",
        "cohort_type": "mutation",
        "rule": "driver_score >= 11 and avg_turnover_20_ntd >= 20,000,000",
    },
    {
        "variant": "BALANCED_RISK_GUARD",
        "cohort_type": "mutation",
        "rule": (
            "driver_score >= 11; no late-chase/upper-tail/volume-exhaustion; "
            "close_to_sma5_pct <= 12; avg_turnover_20_ntd >= 20,000,000"
        ),
    },
    {
        "variant": "SECTOR_NEUTRAL_SCORE_8",
        "cohort_type": "mutation",
        "rule": "driver_score minus sector points >= 8",
    },
]

YEARLY_WALK_FORWARD_FOLDS = [
    {
        "fold_id": "WF_2023_SELECT_2024_TEST",
        "development_end": "2022-12-31",
        "validation_end": "2023-12-31",
        "holdout_end": "2024-12-31",
    },
    {
        "fold_id": "WF_2024_SELECT_2025_TEST",
        "development_end": "2023-12-31",
        "validation_end": "2024-12-31",
        "holdout_end": "2025-12-31",
    },
    {
        "fold_id": "WF_2025_SELECT_2026H1_TEST",
        "development_end": "2024-12-31",
        "validation_end": "2025-12-31",
        "holdout_end": "2026-06-10",
    },
]

EVALUATOR_ONLY_COLUMNS = {
    "entry_date",
    "entry_adj_open",
    "exit_date",
    "exit_adj_close",
    "gross_return_pct",
    "net_return_pct",
    "corporate_action_event_in_horizon",
    "entry_gap_pct",
}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])
    candidate_paths = [args.candidates_csv, *args.additional_candidates_csv]
    candidates = load_candidate_files(
        [REPO_ROOT / path for path in candidate_paths],
    )
    daily_features = load_daily_features(candidates, sqlite_path=sqlite_path)
    scored = score_driver_screen(candidates, daily_features=daily_features)
    scored = add_asof_experiment_features(scored)
    adjusted_prices = load_adjusted_prices(
        candidates,
        sqlite_path=sqlite_path,
        horizon_trading_days=args.horizon_trading_days,
    )
    labeled = attach_execution_labels(
        scored,
        adjusted_prices=adjusted_prices,
        horizon_trading_days=args.horizon_trading_days,
        brokerage_fee_rate=args.brokerage_fee_rate,
        sell_tax_rate=args.sell_tax_rate,
        one_way_slippage_rate=args.one_way_slippage_rate,
    )
    result = run_strategy_experiment(
        labeled,
        adjusted_prices=adjusted_prices,
        development_end=args.development_end,
        validation_end=args.validation_end,
        holdout_end=args.holdout_end,
        horizon_trading_days=args.horizon_trading_days,
        minimum_validation_rows=args.minimum_validation_rows,
        minimum_validation_coverage=args.minimum_validation_coverage,
    )
    result["summary"]["cost_assumptions"] = {
        "brokerage_fee_rate_each_side": args.brokerage_fee_rate,
        "sell_tax_rate": args.sell_tax_rate,
        "one_way_slippage_rate": args.one_way_slippage_rate,
        "official_reference_urls": [
            "https://www.twse.com.tw/zh/about/company/guide.html",
            (
                "https://twse-regulation.twse.com.tw/EN/law/"
                "DOC01_print.aspx?FLCODE=FL007304&FLNO=94"
            ),
        ],
    }
    result["summary"]["source"] = {
        "candidates_csvs": candidate_paths,
        "sqlite_path": str(sqlite_path),
        "adjusted_price_table": "tw_adjusted_ohlcv_daily",
        "adjusted_price_asof": _latest_adjusted_asof(adjusted_prices),
    }
    if args.run_yearly_walk_forward:
        walk_forward = run_yearly_walk_forward_review(
            labeled,
            adjusted_prices=adjusted_prices,
            horizon_trading_days=args.horizon_trading_days,
            minimum_validation_rows=args.minimum_validation_rows,
            minimum_validation_coverage=args.minimum_validation_coverage,
        )
        result["walk_forward_metrics"] = walk_forward["metrics"]
        result["walk_forward_reviews"] = walk_forward["reviews"]
        result["summary"]["walk_forward_review"] = walk_forward["summary"]
        if walk_forward["summary"]["replication_decision"] == (
            "blocked_before_promotion_review"
        ):
            result["summary"]["promotion_decision"] = (
                "blocked_before_promotion_review"
            )
    output_dir = REPO_ROOT / args.output_dir
    write_outputs(result, output_dir=output_dir)
    print(f"mode={MODE}")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"selected_by_validation={result['summary']['selection']['selected_variant']}")
    print(f"promotion_decision={result['summary']['promotion_decision']}")
    print(f"summary_md={output_dir / 'zhu_walkline_strategy_experiment_summary.md'}")
    return 0


def add_asof_experiment_features(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    close = pd.to_numeric(output.get("close"), errors="coerce")
    volume = pd.to_numeric(output.get("volume"), errors="coerce")
    volume_ma20 = pd.to_numeric(output.get("volume_ma20"), errors="coerce")
    output["signal_turnover_ntd"] = close * volume
    output["avg_turnover_20_ntd"] = close * volume_ma20
    sector_points = pd.Series(0.0, index=output.index)
    sector = output.get("sector", pd.Series("", index=output.index)).fillna("").astype(str)
    sector_points.loc[sector.eq("電子零組件")] = 3.0
    sector_points.loc[sector.isin(["光電", "其他電子"])] = 1.0
    output["driver_sector_points"] = sector_points
    output["sector_neutral_driver_score"] = (
        pd.to_numeric(output.get("driver_score"), errors="coerce") - sector_points
    )
    return output


def load_candidate_files(paths: list[Path]) -> pd.DataFrame:
    if not paths:
        raise ValueError("at least one candidate CSV is required")
    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = pd.read_csv(path, dtype={"stock_id": str}, low_memory=False)
        frame["_candidate_source"] = str(path)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["stock_id"] = combined["stock_id"].astype(str).str.zfill(4)
    combined["asof_date"] = pd.to_datetime(combined["asof_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    return combined.drop_duplicates(
        ["asof_date", "stock_id", "early_observation_rule"], keep="last"
    ).sort_values(["asof_date", "stock_id"])


def build_variant_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    forbidden = EVALUATOR_ONLY_COLUMNS.intersection(
        {
            "driver_score",
            "late_chase_risk_flag",
            "upper_tail_flag",
            "volume_exhaustion_flag",
            "close_to_sma5_pct",
            "avg_turnover_20_ntd",
            "sector_neutral_driver_score",
        }
    )
    if forbidden:
        raise AssertionError(f"variant fields include evaluator-only columns: {sorted(forbidden)}")
    score = pd.to_numeric(frame.get("driver_score"), errors="coerce")
    ma5_gap = pd.to_numeric(frame.get("close_to_sma5_pct"), errors="coerce")
    liquidity = pd.to_numeric(frame.get("avg_turnover_20_ntd"), errors="coerce")
    sector_neutral_score = pd.to_numeric(
        frame.get("sector_neutral_driver_score"), errors="coerce"
    )
    no_late_chase = _clean_flag(frame, "late_chase_risk_flag")
    no_upper_tail = _clean_flag(frame, "upper_tail_flag")
    no_volume_exhaustion = _clean_flag(frame, "volume_exhaustion_flag")
    baseline = score >= 11.0
    return {
        BASELINE_VARIANT: baseline,
        "SCORE_12": score >= 12.0,
        "BASELINE_NO_LATE_CHASE": baseline & no_late_chase,
        "BASELINE_NO_UPPER_TAIL": baseline & no_upper_tail,
        "BASELINE_NO_VOLUME_EXHAUSTION": baseline & no_volume_exhaustion,
        "BASELINE_MA5_GAP_CAP_12": baseline & ma5_gap.le(12.0) & ma5_gap.notna(),
        "BASELINE_LIQUIDITY_20M": baseline & liquidity.ge(20_000_000.0),
        "BALANCED_RISK_GUARD": (
            baseline
            & no_late_chase
            & no_upper_tail
            & no_volume_exhaustion
            & ma5_gap.le(12.0)
            & ma5_gap.notna()
            & liquidity.ge(20_000_000.0)
        ),
        "SECTOR_NEUTRAL_SCORE_8": sector_neutral_score.ge(8.0),
    }


def attach_execution_labels(
    frame: pd.DataFrame,
    *,
    adjusted_prices: pd.DataFrame,
    horizon_trading_days: int,
    brokerage_fee_rate: float,
    sell_tax_rate: float,
    one_way_slippage_rate: float,
) -> pd.DataFrame:
    """Attach evaluator-only next-open to D+N adjusted-price labels."""
    if horizon_trading_days < 2:
        raise ValueError("horizon_trading_days must be at least 2")
    output = frame.drop(columns=list(EVALUATOR_ONLY_COLUMNS), errors="ignore").copy()
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["asof_date"] = pd.to_datetime(output["asof_date"]).dt.strftime("%Y-%m-%d")
    prices = adjusted_prices.copy()
    if prices.empty:
        return _add_empty_execution_columns(output)
    prices["date"] = pd.to_datetime(prices["date"])
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    prices = prices.sort_values(["stock_id", "date"]).drop_duplicates(
        ["stock_id", "date"], keep="last"
    )
    numeric_columns = [
        "adj_open",
        "adj_close",
        "adjustment_factor",
        "factor_event_count",
    ]
    for column in numeric_columns:
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    grouped = prices.groupby("stock_id", group_keys=False)
    label_rows = prices[["date", "stock_id", "adj_close", "adjustment_factor"]].copy()
    label_rows = label_rows.rename(
        columns={
            "date": "asof_date",
            "adj_close": "signal_adj_close",
            "adjustment_factor": "signal_adjustment_factor",
        }
    )
    label_rows["entry_date"] = grouped["date"].shift(-1)
    label_rows["entry_adj_open"] = grouped["adj_open"].shift(-1)
    label_rows["exit_date"] = grouped["date"].shift(-horizon_trading_days)
    label_rows["exit_adj_close"] = grouped["adj_close"].shift(-horizon_trading_days)
    label_rows["exit_adjustment_factor"] = grouped["adjustment_factor"].shift(
        -horizon_trading_days
    )
    label_rows["exit_factor_event_count"] = grouped["factor_event_count"].shift(
        -horizon_trading_days
    )
    label_rows["asof_date"] = label_rows["asof_date"].dt.strftime("%Y-%m-%d")
    merged = output.merge(label_rows, on=["asof_date", "stock_id"], how="left")
    entry = pd.to_numeric(merged["entry_adj_open"], errors="coerce")
    exit_close = pd.to_numeric(merged["exit_adj_close"], errors="coerce")
    signal_close = pd.to_numeric(merged["signal_adj_close"], errors="coerce")
    merged["gross_return_pct"] = ((exit_close / entry) - 1.0) * 100.0
    buy_multiplier = 1.0 + brokerage_fee_rate + one_way_slippage_rate
    sell_multiplier = 1.0 - brokerage_fee_rate - sell_tax_rate - one_way_slippage_rate
    merged["net_return_pct"] = (
        ((exit_close * sell_multiplier) / (entry * buy_multiplier)) - 1.0
    ) * 100.0
    merged["entry_gap_pct"] = ((entry / signal_close) - 1.0) * 100.0
    signal_factor = pd.to_numeric(merged["signal_adjustment_factor"], errors="coerce")
    exit_factor = pd.to_numeric(merged["exit_adjustment_factor"], errors="coerce")
    merged["corporate_action_event_in_horizon"] = (
        signal_factor.notna()
        & exit_factor.notna()
        & ((signal_factor - exit_factor).abs() > 1e-12)
    )
    merged["label_mature"] = entry.notna() & exit_close.notna()
    for column in ["entry_date", "exit_date"]:
        merged[column] = pd.to_datetime(merged[column], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )
    return merged


def run_strategy_experiment(
    labeled: pd.DataFrame,
    *,
    adjusted_prices: pd.DataFrame,
    development_end: str,
    validation_end: str,
    holdout_end: str,
    horizon_trading_days: int,
    minimum_validation_rows: int,
    minimum_validation_coverage: float,
) -> dict[str, Any]:
    frame = assign_temporal_split(
        labeled,
        development_end=development_end,
        validation_end=validation_end,
        holdout_end=holdout_end,
    )
    frame = frame[frame["split"].ne("")].copy()
    frame = frame[pd.to_numeric(frame["net_return_pct"], errors="coerce").notna()].copy()
    masks = build_variant_masks(frame)
    for variant, mask in masks.items():
        frame[f"variant__{variant}"] = mask.fillna(False).astype(bool)
    variant_frames = {variant: frame[mask.fillna(False)].copy() for variant, mask in masks.items()}
    baseline_selected = variant_frames[BASELINE_VARIANT]
    baseline_cohorts = build_same_count_baselines(baseline_selected, frame)
    cohort_frames = {
        **variant_frames,
        "ALL_CANDIDATES": frame,
        "SAME_COUNT_TOP_RISE": baseline_cohorts["same_count_top_rise"],
        "SAME_COUNT_RANDOM": baseline_cohorts["same_count_random"],
    }
    cohort_types = {spec["variant"]: spec["cohort_type"] for spec in VARIANT_SPECS}
    cohort_types.update(
        {
            "ALL_CANDIDATES": "comparison",
            "SAME_COUNT_TOP_RISE": "comparison",
            "SAME_COUNT_RANDOM": "comparison",
        }
    )
    trading_dates = sorted(
        pd.to_datetime(adjusted_prices.get("date"), errors="coerce")
        .dropna()
        .dt.strftime("%Y-%m-%d")
        .unique()
    )
    metrics = compute_experiment_metrics(
        cohort_frames,
        cohort_types=cohort_types,
        trading_dates=trading_dates,
        horizon_trading_days=horizon_trading_days,
    )
    quarterly = compute_quarterly_metrics(
        cohort_frames,
        cohort_types=cohort_types,
        trading_dates=trading_dates,
        horizon_trading_days=horizon_trading_days,
    )
    failure_attribution = compute_failure_attribution(
        baseline_selected,
        trading_dates=trading_dates,
        horizon_trading_days=horizon_trading_days,
    )
    selection = select_variant_from_validation(
        metrics,
        minimum_validation_rows=minimum_validation_rows,
        minimum_validation_coverage=minimum_validation_coverage,
    )
    promotion_decision, holdout_review = review_holdout(metrics, selection=selection)
    research_recommendations = derive_post_holdout_research_recommendations(metrics)
    selected_variant = selection["selected_variant"]
    selected_rows = variant_frames[selected_variant].copy()
    summary = {
        "mode": MODE,
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "purpose": "zhu_walkline_full_strategy_experiment_sidecar",
        "prediction_task": {
            "market": "Taiwan TWSE/TPEx common stocks",
            "currency": "TWD",
            "timezone": "Asia/Taipei",
            "horizon_trading_days": horizon_trading_days,
            "target": "next-open to D+20 adjusted net return",
            "signal_time": "after as-of close",
            "entry_assumption": "next trading day adjusted open",
            "exit_assumption": "as-of plus 20 trading days adjusted close",
        },
        "temporal_split": {
            "development_end": development_end,
            "validation_end": validation_end,
            "holdout_end": holdout_end,
            "variant_selection_uses": "validation only",
            "holdout_used_for_selection": False,
        },
        "variant_specs": VARIANT_SPECS,
        "variant_count": len(VARIANT_SPECS),
        "selection": selection,
        "holdout_review": holdout_review,
        "research_recommendations": research_recommendations,
        "promotion_decision": promotion_decision,
        "multiple_testing_guard": (
            "fixed finite variants; validation-only selection; 2026 holdout locked until review"
        ),
        "corporate_action_treatment": (
            "adjusted OHLCV labels; separate no-corporate-action robustness scope"
        ),
        "liquidity_treatment": (
            "as-of 20-day average traded value reported; explicit 20M gate variants"
        ),
        "overlap_treatment": (
            "primary review uses a 20-trading-day same-stock signal cooldown"
        ),
        "failure_attribution": [
            "repeated same-stock signals can inflate raw row counts",
            "signal-close entry is not executable and was replaced by next-open entry",
            "sector hard points may be regime-specific",
            "late-chase, upper-tail, and volume-exhaustion flags may identify fragile breakouts",
        ],
        "top_failure_buckets": _records_for_json(
            failure_attribution[
                pd.to_numeric(failure_attribution["rows"], errors="coerce") >= 30
            ]
            .sort_values(
                ["tail_loss_rate_net_le_neg10", "downside_rate_net_lt_0"],
                ascending=[False, False],
            )
            .head(12)
        ),
        "no_lookahead": {
            "variant_membership_uses_asof_fields_only": True,
            "adjusted_entry_exit_are_evaluator_only": True,
            "corporate_action_horizon_flag_is_evaluator_only": True,
        },
        "max_drawdown_note": (
            "not reported because this sidecar does not simulate capital allocation or a portfolio NAV"
        ),
        "no_formal_strategy_modified": True,
        "no_formal_champion_modified": True,
        "no_formal_trade_effect": True,
    }
    return {
        "labeled_rows": frame,
        "selected_rows": selected_rows,
        "metrics": metrics,
        "quarterly_metrics": quarterly,
        "failure_attribution": failure_attribution,
        "summary": summary,
    }


def derive_post_holdout_research_recommendations(
    metrics: pd.DataFrame,
) -> dict[str, Any]:
    scoped = metrics[
        metrics["evaluation_scope"].eq(EVALUATION_SCOPE)
        & metrics["split"].isin(["validation", "holdout"])
        & metrics["cohort_type"].isin(["baseline", "mutation"])
    ].copy()
    baseline = scoped[scoped["variant"].eq(BASELINE_VARIANT)].set_index("split")
    if not {"validation", "holdout"}.issubset(baseline.index):
        return {
            "post_holdout_only": True,
            "risk_control_candidate": "",
            "reason": "validation or holdout baseline is missing",
        }
    no_effect_variants: list[str] = []
    risk_candidates: list[dict[str, Any]] = []
    for variant in scoped[scoped["cohort_type"].eq("mutation")]["variant"].unique():
        rows = scoped[scoped["variant"].eq(variant)].set_index("split")
        if not {"validation", "holdout"}.issubset(rows.index):
            continue
        if all(
            int(rows.loc[split, "rows"]) == int(baseline.loc[split, "rows"])
            and _nearly_equal(
                rows.loc[split, "avg_net_return_pct"],
                baseline.loc[split, "avg_net_return_pct"],
            )
            and _nearly_equal(
                rows.loc[split, "tail_loss_rate_net_le_neg10"],
                baseline.loc[split, "tail_loss_rate_net_le_neg10"],
            )
            for split in ["validation", "holdout"]
        ):
            no_effect_variants.append(str(variant))
            continue
        validation_coverage = float(rows.loc["validation", "rows"]) / float(
            baseline.loc["validation", "rows"]
        )
        holdout_coverage = float(rows.loc["holdout", "rows"]) / float(
            baseline.loc["holdout", "rows"]
        )
        replicated_risk_control = bool(
            validation_coverage >= 0.50
            and holdout_coverage >= 0.50
            and _ge(
                rows.loc["validation", "median_net_return_pct"],
                baseline.loc["validation", "median_net_return_pct"],
            )
            and _ge(
                rows.loc["holdout", "median_net_return_pct"],
                baseline.loc["holdout", "median_net_return_pct"],
            )
            and _le(
                rows.loc["validation", "tail_loss_rate_net_le_neg10"],
                baseline.loc["validation", "tail_loss_rate_net_le_neg10"],
            )
            and _le(
                rows.loc["holdout", "tail_loss_rate_net_le_neg10"],
                baseline.loc["holdout", "tail_loss_rate_net_le_neg10"],
            )
            and _le(
                rows.loc["validation", "downside_rate_net_lt_0"],
                baseline.loc["validation", "downside_rate_net_lt_0"],
            )
            and _le(
                rows.loc["holdout", "downside_rate_net_lt_0"],
                _float_or(baseline.loc["holdout", "downside_rate_net_lt_0"], 1.0)
                + 0.01,
            )
            and _ge(
                rows.loc["holdout", "avg_net_return_pct"],
                _float_or(baseline.loc["holdout", "avg_net_return_pct"], 0.0)
                - 0.25,
            )
        )
        if replicated_risk_control:
            risk_candidates.append(
                {
                    "variant": str(variant),
                    "validation_coverage": validation_coverage,
                    "holdout_coverage": holdout_coverage,
                    "holdout_avg_return_delta": _float_or(
                        rows.loc["holdout", "avg_net_return_pct"], 0.0
                    )
                    - _float_or(
                        baseline.loc["holdout", "avg_net_return_pct"], 0.0
                    ),
                    "holdout_median_return_delta": _float_or(
                        rows.loc["holdout", "median_net_return_pct"], 0.0
                    )
                    - _float_or(
                        baseline.loc["holdout", "median_net_return_pct"], 0.0
                    ),
                    "holdout_tail_loss_delta": _float_or(
                        rows.loc["holdout", "tail_loss_rate_net_le_neg10"], 1.0
                    )
                    - _float_or(
                        baseline.loc["holdout", "tail_loss_rate_net_le_neg10"],
                        1.0,
                    ),
                }
            )
    if risk_candidates:
        risk_candidates.sort(
            key=lambda item: (
                item["holdout_tail_loss_delta"],
                -item["holdout_coverage"],
            )
        )
        risk_candidate = risk_candidates[0]["variant"]
        reason = (
            "candidate improved median and tail-risk metrics in validation and holdout; "
            "because it was identified after holdout inspection it requires new replication"
        )
    else:
        risk_candidate = ""
        reason = "no mutation met the post-holdout replicated risk-control diagnostic"
    return {
        "post_holdout_only": True,
        "not_eligible_for_current_selection": True,
        "risk_control_candidate": risk_candidate,
        "risk_candidate_reviews": risk_candidates,
        "signal_date_no_effect_variants": no_effect_variants,
        "reason": reason,
    }


def run_yearly_walk_forward_review(
    labeled: pd.DataFrame,
    *,
    adjusted_prices: pd.DataFrame,
    horizon_trading_days: int,
    minimum_validation_rows: int,
    minimum_validation_coverage: float,
) -> dict[str, Any]:
    dates = pd.to_datetime(labeled["asof_date"], errors="coerce").dropna()
    if dates.empty:
        raise ValueError("walk-forward review requires dated labeled rows")
    available_start = dates.min()
    available_end = dates.max()
    metric_frames: list[pd.DataFrame] = []
    review_rows: list[dict[str, Any]] = []
    for fold in YEARLY_WALK_FORWARD_FOLDS:
        if available_start > pd.Timestamp(fold["development_end"]):
            continue
        if available_end < pd.Timestamp(fold["holdout_end"]):
            continue
        result = run_strategy_experiment(
            labeled,
            adjusted_prices=adjusted_prices,
            development_end=fold["development_end"],
            validation_end=fold["validation_end"],
            holdout_end=fold["holdout_end"],
            horizon_trading_days=horizon_trading_days,
            minimum_validation_rows=minimum_validation_rows,
            minimum_validation_coverage=minimum_validation_coverage,
        )
        fold_metrics = result["metrics"].copy()
        fold_metrics.insert(0, "fold_id", fold["fold_id"])
        metric_frames.append(fold_metrics)
        selection = result["summary"]["selection"]
        holdout_review = result["summary"]["holdout_review"]
        selected_metrics = holdout_review.get("selected_metrics", {})
        baseline_metrics = holdout_review.get("baseline_metrics", {})
        review_rows.append(
            {
                **fold,
                "selected_variant": selection["selected_variant"],
                "promotion_decision": result["summary"]["promotion_decision"],
                "holdout_passed": bool(holdout_review.get("passed", False)),
                "selected_holdout_rows": selected_metrics.get("rows"),
                "selected_holdout_avg_net_return_pct": selected_metrics.get(
                    "avg_net_return_pct"
                ),
                "baseline_holdout_avg_net_return_pct": baseline_metrics.get(
                    "avg_net_return_pct"
                ),
                "selected_holdout_median_net_return_pct": selected_metrics.get(
                    "median_net_return_pct"
                ),
                "baseline_holdout_median_net_return_pct": baseline_metrics.get(
                    "median_net_return_pct"
                ),
                "selected_holdout_tail_loss_rate": selected_metrics.get(
                    "tail_loss_rate_net_le_neg10"
                ),
                "baseline_holdout_tail_loss_rate": baseline_metrics.get(
                    "tail_loss_rate_net_le_neg10"
                ),
                "review_reason": holdout_review.get("reason", ""),
            }
        )
    if not review_rows:
        raise ValueError("no complete yearly walk-forward folds are available")
    reviews = _round_numeric(pd.DataFrame(review_rows))
    passed = reviews[reviews["holdout_passed"].astype(bool)]
    passed_counts = passed["selected_variant"].value_counts()
    replicated_variant = ""
    if not passed_counts.empty and int(passed_counts.iloc[0]) >= 2:
        replicated_variant = str(passed_counts.index[0])
    replication_decision = (
        "advisory_candidate"
        if replicated_variant
        else "blocked_before_promotion_review"
    )
    summary = {
        "fold_count": int(len(reviews)),
        "holdout_pass_count": int(reviews["holdout_passed"].astype(bool).sum()),
        "selected_variant_counts": {
            str(key): int(value)
            for key, value in reviews["selected_variant"].value_counts().items()
        },
        "passed_variant_counts": {
            str(key): int(value) for key, value in passed_counts.items()
        },
        "replicated_variant": replicated_variant,
        "replication_decision": replication_decision,
        "minimum_required_repeated_holdout_passes": 2,
        "folds": _records_for_json(reviews),
    }
    metrics = (
        pd.concat(metric_frames, ignore_index=True)
        if metric_frames
        else pd.DataFrame()
    )
    return {"metrics": metrics, "reviews": reviews, "summary": summary}


def rebuild_walk_forward_review_from_metrics(
    metrics: pd.DataFrame,
    *,
    minimum_validation_rows: int,
    minimum_validation_coverage: float,
) -> dict[str, Any]:
    review_rows: list[dict[str, Any]] = []
    for fold in YEARLY_WALK_FORWARD_FOLDS:
        fold_metrics = metrics[metrics["fold_id"].eq(fold["fold_id"])].copy()
        if fold_metrics.empty:
            continue
        selection = select_variant_from_validation(
            fold_metrics,
            minimum_validation_rows=minimum_validation_rows,
            minimum_validation_coverage=minimum_validation_coverage,
        )
        decision, holdout_review = review_holdout(
            fold_metrics,
            selection=selection,
        )
        selected_metrics = holdout_review.get("selected_metrics", {})
        baseline_metrics = holdout_review.get("baseline_metrics", {})
        review_rows.append(
            {
                **fold,
                "selected_variant": selection["selected_variant"],
                "promotion_decision": decision,
                "holdout_passed": bool(holdout_review.get("passed", False)),
                "selected_holdout_rows": selected_metrics.get("rows"),
                "selected_holdout_avg_net_return_pct": selected_metrics.get(
                    "avg_net_return_pct"
                ),
                "baseline_holdout_avg_net_return_pct": baseline_metrics.get(
                    "avg_net_return_pct"
                ),
                "selected_holdout_median_net_return_pct": selected_metrics.get(
                    "median_net_return_pct"
                ),
                "baseline_holdout_median_net_return_pct": baseline_metrics.get(
                    "median_net_return_pct"
                ),
                "selected_holdout_tail_loss_rate": selected_metrics.get(
                    "tail_loss_rate_net_le_neg10"
                ),
                "baseline_holdout_tail_loss_rate": baseline_metrics.get(
                    "tail_loss_rate_net_le_neg10"
                ),
                "review_reason": holdout_review.get("reason", ""),
            }
        )
    if not review_rows:
        raise ValueError("walk-forward metrics contain no configured folds")
    reviews = _round_numeric(pd.DataFrame(review_rows))
    passed = reviews[reviews["holdout_passed"].astype(bool)]
    passed_counts = passed["selected_variant"].value_counts()
    replicated_variant = ""
    if not passed_counts.empty and int(passed_counts.iloc[0]) >= 2:
        replicated_variant = str(passed_counts.index[0])
    summary = {
        "fold_count": int(len(reviews)),
        "holdout_pass_count": int(reviews["holdout_passed"].astype(bool).sum()),
        "selected_variant_counts": {
            str(key): int(value)
            for key, value in reviews["selected_variant"].value_counts().items()
        },
        "passed_variant_counts": {
            str(key): int(value) for key, value in passed_counts.items()
        },
        "replicated_variant": replicated_variant,
        "replication_decision": (
            "advisory_candidate"
            if replicated_variant
            else "blocked_before_promotion_review"
        ),
        "minimum_required_repeated_holdout_passes": 2,
        "folds": _records_for_json(reviews),
    }
    return {"reviews": reviews, "summary": summary}


def assign_temporal_split(
    frame: pd.DataFrame,
    *,
    development_end: str,
    validation_end: str,
    holdout_end: str,
) -> pd.DataFrame:
    development_ts = pd.Timestamp(development_end)
    validation_ts = pd.Timestamp(validation_end)
    holdout_ts = pd.Timestamp(holdout_end)
    if not development_ts < validation_ts < holdout_ts:
        raise ValueError("temporal boundaries must be development < validation < holdout")
    output = frame.copy()
    dates = pd.to_datetime(output["asof_date"], errors="coerce")
    output["split"] = ""
    output.loc[dates.le(development_ts), "split"] = "development"
    output.loc[dates.gt(development_ts) & dates.le(validation_ts), "split"] = (
        "validation"
    )
    output.loc[dates.gt(validation_ts) & dates.le(holdout_ts), "split"] = "holdout"
    return output


def compute_experiment_metrics(
    cohort_frames: dict[str, pd.DataFrame],
    *,
    cohort_types: dict[str, str],
    trading_dates: list[str],
    horizon_trading_days: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for cohort, frame in cohort_frames.items():
        scopes = _evaluation_scopes(
            frame,
            trading_dates=trading_dates,
            horizon_trading_days=horizon_trading_days,
        )
        for scope_name, scoped in scopes.items():
            for split in ["development", "validation", "holdout", "all"]:
                group = scoped if split == "all" else scoped[scoped["split"].eq(split)]
                records.append(
                    {
                        "variant": cohort,
                        "cohort_type": cohort_types[cohort],
                        "evaluation_scope": scope_name,
                        "split": split,
                        **return_metrics(group),
                    }
                )
    return _round_numeric(pd.DataFrame(records))


def compute_quarterly_metrics(
    cohort_frames: dict[str, pd.DataFrame],
    *,
    cohort_types: dict[str, str],
    trading_dates: list[str],
    horizon_trading_days: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for cohort, frame in cohort_frames.items():
        scopes = _evaluation_scopes(
            frame,
            trading_dates=trading_dates,
            horizon_trading_days=horizon_trading_days,
        )
        for scope_name, scoped in scopes.items():
            data = scoped.copy()
            data["quarter"] = pd.PeriodIndex(
                pd.to_datetime(data["asof_date"]), freq="Q"
            ).astype(str)
            for quarter, group in data.groupby("quarter"):
                records.append(
                    {
                        "variant": cohort,
                        "cohort_type": cohort_types[cohort],
                        "evaluation_scope": scope_name,
                        "quarter": quarter,
                        "split": str(group["split"].mode().iloc[0]),
                        **return_metrics(group),
                    }
                )
    return _round_numeric(pd.DataFrame(records))


def compute_failure_attribution(
    baseline_frame: pd.DataFrame,
    *,
    trading_dates: list[str],
    horizon_trading_days: int,
) -> pd.DataFrame:
    data = apply_signal_cooldown(
        baseline_frame,
        trading_dates=trading_dates,
        cooldown_trading_days=horizon_trading_days,
    ).copy()
    if data.empty:
        return pd.DataFrame(
            columns=["dimension", "bucket", "split", *return_metrics(data).keys()]
        )
    data["quarter"] = pd.PeriodIndex(
        pd.to_datetime(data["asof_date"]), freq="Q"
    ).astype(str)
    data["driver_score_bucket"] = pd.to_numeric(
        data["driver_score"], errors="coerce"
    ).round().astype("Int64").astype(str)
    entry_gap_bucket = pd.cut(
        pd.to_numeric(data["entry_gap_pct"], errors="coerce"),
        [-float("inf"), 0.0, 2.0, 5.0, float("inf")],
        labels=[
            "ENTRY_GAP_LE_0",
            "ENTRY_GAP_0_2",
            "ENTRY_GAP_2_5",
            "ENTRY_GAP_GT_5",
        ],
    ).astype("object")
    data["entry_gap_bucket"] = entry_gap_bucket.where(
        pd.notna(entry_gap_bucket), "MISSING"
    )
    ma5_gap_bucket = pd.cut(
        pd.to_numeric(data["close_to_sma5_pct"], errors="coerce"),
        [-float("inf"), 5.0, 8.0, 12.0, float("inf")],
        labels=[
            "MA5_GAP_LE_5",
            "MA5_GAP_5_8",
            "MA5_GAP_8_12",
            "MA5_GAP_GT_12",
        ],
    ).astype("object")
    data["ma5_gap_bucket"] = ma5_gap_bucket.where(
        pd.notna(ma5_gap_bucket), "MISSING"
    )
    dimensions = [
        "quarter",
        "market_state",
        "sector_state",
        "driver_score_bucket",
        "entry_gap_bucket",
        "ma5_gap_bucket",
    ]
    records: list[dict[str, Any]] = []
    for dimension in dimensions:
        for (split, bucket), group in data.groupby(["split", dimension], dropna=False):
            records.append(
                {
                    "dimension": dimension,
                    "bucket": str(bucket),
                    "split": str(split),
                    "feature_timing": (
                        "entry_time" if dimension == "entry_gap_bucket" else "signal_time"
                    ),
                    **return_metrics(group),
                }
            )
    return _round_numeric(pd.DataFrame(records))


def return_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "unique_stocks": 0,
            "date_count": 0,
            "avg_gross_return_pct": None,
            "avg_net_return_pct": None,
            "median_net_return_pct": None,
            "daily_equal_weight_avg_net_return_pct": None,
            "hit_rate_net_gt_0": None,
            "hit_rate_net_ge_20": None,
            "downside_rate_net_lt_0": None,
            "tail_loss_rate_net_le_neg10": None,
            "avg_entry_gap_pct": None,
            "corporate_action_event_rate": None,
            "avg_turnover_20_ntd": None,
        }
    gross = pd.to_numeric(frame["gross_return_pct"], errors="coerce")
    net = pd.to_numeric(frame["net_return_pct"], errors="coerce")
    valid = frame[net.notna()].copy()
    gross = pd.to_numeric(valid["gross_return_pct"], errors="coerce")
    net = pd.to_numeric(valid["net_return_pct"], errors="coerce")
    daily_returns = valid.assign(_net=net).groupby("asof_date")["_net"].mean()
    corporate = valid["corporate_action_event_in_horizon"].fillna(False).astype(bool)
    return {
        "rows": int(len(valid)),
        "unique_stocks": int(valid["stock_id"].nunique()),
        "date_count": int(valid["asof_date"].nunique()),
        "avg_gross_return_pct": gross.mean(),
        "avg_net_return_pct": net.mean(),
        "median_net_return_pct": net.median(),
        "daily_equal_weight_avg_net_return_pct": daily_returns.mean(),
        "hit_rate_net_gt_0": net.gt(0.0).mean(),
        "hit_rate_net_ge_20": net.ge(20.0).mean(),
        "downside_rate_net_lt_0": net.lt(0.0).mean(),
        "tail_loss_rate_net_le_neg10": net.le(-10.0).mean(),
        "avg_entry_gap_pct": pd.to_numeric(
            valid["entry_gap_pct"], errors="coerce"
        ).mean(),
        "corporate_action_event_rate": corporate.mean(),
        "avg_turnover_20_ntd": pd.to_numeric(
            valid["avg_turnover_20_ntd"], errors="coerce"
        ).mean(),
    }


def select_variant_from_validation(
    metrics: pd.DataFrame,
    *,
    minimum_validation_rows: int,
    minimum_validation_coverage: float,
) -> dict[str, Any]:
    validation = metrics[
        metrics["split"].eq("validation")
        & metrics["evaluation_scope"].eq(EVALUATION_SCOPE)
        & metrics["cohort_type"].isin(["baseline", "mutation"])
    ].copy()
    baseline_rows = validation[validation["variant"].eq(BASELINE_VARIANT)]
    if baseline_rows.empty:
        raise ValueError("validation baseline metrics are missing")
    baseline = baseline_rows.iloc[0]
    base_count = int(baseline["rows"])
    candidates: list[dict[str, Any]] = []
    for _, row in validation[validation["cohort_type"].eq("mutation")].iterrows():
        coverage = (float(row["rows"]) / base_count) if base_count else 0.0
        no_effect_vs_baseline = bool(
            int(row["rows"]) == base_count
            and _nearly_equal(
                row["avg_net_return_pct"], baseline["avg_net_return_pct"]
            )
            and _nearly_equal(
                row["median_net_return_pct"],
                baseline["median_net_return_pct"],
            )
            and _nearly_equal(
                row["tail_loss_rate_net_le_neg10"],
                baseline["tail_loss_rate_net_le_neg10"],
            )
            and _nearly_equal(
                row["downside_rate_net_lt_0"],
                baseline["downside_rate_net_lt_0"],
            )
        )
        pass_gate = bool(
            not no_effect_vs_baseline
            and int(row["rows"]) >= minimum_validation_rows
            and coverage >= minimum_validation_coverage
            and _ge(row["avg_net_return_pct"], baseline["avg_net_return_pct"])
            and _ge(row["median_net_return_pct"], baseline["median_net_return_pct"])
            and _le(
                row["tail_loss_rate_net_le_neg10"],
                baseline["tail_loss_rate_net_le_neg10"],
            )
            and _le(
                row["downside_rate_net_lt_0"],
                baseline["downside_rate_net_lt_0"],
            )
        )
        robust_score = (
            _float_or(row["avg_net_return_pct"], -999.0)
            + _float_or(row["median_net_return_pct"], -999.0)
            + 5.0 * _float_or(row["hit_rate_net_ge_20"], 0.0)
            - 10.0 * _float_or(row["tail_loss_rate_net_le_neg10"], 1.0)
        )
        candidates.append(
            {
                "variant": row["variant"],
                "rows": int(row["rows"]),
                "coverage_vs_baseline": coverage,
                "no_effect_vs_baseline": no_effect_vs_baseline,
                "pass_validation_gate": pass_gate,
                "validation_robust_score": robust_score,
                "avg_net_return_pct": row["avg_net_return_pct"],
                "median_net_return_pct": row["median_net_return_pct"],
                "tail_loss_rate_net_le_neg10": row[
                    "tail_loss_rate_net_le_neg10"
                ],
                "downside_rate_net_lt_0": row["downside_rate_net_lt_0"],
            }
        )
    passing = [candidate for candidate in candidates if candidate["pass_validation_gate"]]
    if passing:
        selected = max(
            passing,
            key=lambda item: (item["validation_robust_score"], item["rows"]),
        )["variant"]
        reason = "best validation-only mutation passing return, tail, downside, and coverage gates"
    else:
        selected = BASELINE_VARIANT
        reason = "no mutation passed every validation-only robustness gate"
    return {
        "selected_variant": selected,
        "selection_scope": EVALUATION_SCOPE,
        "selection_split": "validation",
        "holdout_used": False,
        "minimum_validation_rows": minimum_validation_rows,
        "minimum_validation_coverage": minimum_validation_coverage,
        "reason": reason,
        "candidate_reviews": _records_for_json(pd.DataFrame(candidates)),
    }


def review_holdout(
    metrics: pd.DataFrame,
    *,
    selection: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    selected_variant = str(selection["selected_variant"])
    holdout = metrics[
        metrics["split"].eq("holdout")
        & metrics["evaluation_scope"].eq(EVALUATION_SCOPE)
    ]
    baseline_rows = holdout[holdout["variant"].eq(BASELINE_VARIANT)]
    selected_rows = holdout[holdout["variant"].eq(selected_variant)]
    if baseline_rows.empty or selected_rows.empty:
        return "blocked_before_promotion_review", {
            "passed": False,
            "reason": "holdout metrics are missing",
        }
    baseline = baseline_rows.iloc[0]
    selected = selected_rows.iloc[0]
    if selected_variant == BASELINE_VARIANT:
        passed = False
        reason = "validation selected the unchanged baseline"
    else:
        minimum_rows = max(30, int(float(baseline["rows"]) * 0.25))
        passed = bool(
            int(selected["rows"]) >= minimum_rows
            and _ge(selected["avg_net_return_pct"], baseline["avg_net_return_pct"])
            and _ge(
                selected["median_net_return_pct"],
                baseline["median_net_return_pct"],
            )
            and _le(
                selected["tail_loss_rate_net_le_neg10"],
                _float_or(baseline["tail_loss_rate_net_le_neg10"], 1.0) + 0.01,
            )
            and _le(
                selected["downside_rate_net_lt_0"],
                _float_or(baseline["downside_rate_net_lt_0"], 1.0) + 0.02,
            )
        )
        reason = (
            "selected validation mutation passed locked holdout gates"
            if passed
            else "selected validation mutation failed one or more locked holdout gates"
        )
    decision = "advisory_candidate" if passed else "blocked_before_promotion_review"
    review = {
        "passed": passed,
        "reason": reason,
        "selected_variant": selected_variant,
        "selected_metrics": _record_for_json(selected.to_dict()),
        "baseline_metrics": _record_for_json(baseline.to_dict()),
    }
    return decision, review


def _evaluation_scopes(
    frame: pd.DataFrame,
    *,
    trading_dates: list[str],
    horizon_trading_days: int,
) -> dict[str, pd.DataFrame]:
    cooldown = apply_signal_cooldown(
        frame,
        trading_dates=trading_dates,
        cooldown_trading_days=horizon_trading_days,
    )
    no_actions = cooldown[
        ~cooldown["corporate_action_event_in_horizon"].fillna(False).astype(bool)
    ].copy()
    return {
        "all_signals": frame,
        EVALUATION_SCOPE: cooldown,
        "cooldown_20d_no_corporate_action": no_actions,
    }


def apply_signal_cooldown(
    frame: pd.DataFrame,
    *,
    trading_dates: list[str],
    cooldown_trading_days: int,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    date_position = {date: index for index, date in enumerate(trading_dates)}
    ordered = frame.copy()
    ordered["_date_position"] = ordered["asof_date"].map(date_position)
    ordered = ordered.dropna(subset=["_date_position"]).copy()
    ordered["_date_position"] = ordered["_date_position"].astype(int)
    ordered = ordered.sort_values(
        ["stock_id", "_date_position", "driver_score"],
        ascending=[True, True, False],
    )
    keep_indices: list[Any] = []
    for _, stock_rows in ordered.groupby("stock_id", sort=False):
        last_position: int | None = None
        for index, row in stock_rows.iterrows():
            current = int(row["_date_position"])
            if last_position is None or current > last_position + cooldown_trading_days:
                keep_indices.append(index)
                last_position = current
    return ordered.loc[keep_indices].drop(columns=["_date_position"]).sort_values(
        ["asof_date", "stock_id"]
    )


def load_daily_features(
    candidates: pd.DataFrame,
    *,
    sqlite_path: Path,
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=DAILY_FEATURE_COLUMNS)
    stock_ids = sorted(
        {str(value).zfill(4) for value in candidates["stock_id"].dropna().unique()}
    )
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select {", ".join(DAILY_FEATURE_COLUMNS)}
        from daily_ohlcv_features
        where date between ? and ?
          and stock_id in ({placeholders})
        order by date, stock_id
    """
    params = [
        str(candidates["asof_date"].min())[:10],
        str(candidates["asof_date"].max())[:10],
        *stock_ids,
    ]
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query, connection, params=params, parse_dates=["date"])


def load_adjusted_prices(
    candidates: pd.DataFrame,
    *,
    sqlite_path: Path,
    horizon_trading_days: int,
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame()
    stock_ids = sorted(
        {str(value).zfill(4) for value in candidates["stock_id"].dropna().unique()}
    )
    placeholders = ",".join("?" for _ in stock_ids)
    calendar_buffer_days = max(60, horizon_trading_days * 4)
    query = f"""
        select date, stock_id, adj_open, adj_close, adjustment_factor,
               factor_event_count, asof_date as adjusted_data_asof
        from tw_adjusted_ohlcv_daily
        where date >= ?
          and date <= date(?, ?)
          and stock_id in ({placeholders})
        order by stock_id, date
    """
    params = [
        str(candidates["asof_date"].min())[:10],
        str(candidates["asof_date"].max())[:10],
        f"+{calendar_buffer_days} day",
        *stock_ids,
    ]
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query, connection, params=params, parse_dates=["date"])


def write_outputs(result: dict[str, Any], *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    labeled = _clean_frame(result["labeled_rows"])
    selected = _clean_frame(result["selected_rows"])
    metrics = _clean_frame(result["metrics"])
    quarterly = _clean_frame(result["quarterly_metrics"])
    labeled.to_csv(
        output_dir / "zhu_walkline_strategy_experiment_rows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    selected.to_csv(
        output_dir / "zhu_walkline_strategy_selected_shadow_rows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    metrics.to_csv(
        output_dir / "zhu_walkline_strategy_experiment_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    quarterly.to_csv(
        output_dir / "zhu_walkline_strategy_experiment_quarterly.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _clean_frame(result["failure_attribution"]).to_csv(
        output_dir / "zhu_walkline_strategy_failure_attribution.csv",
        index=False,
        encoding="utf-8-sig",
    )
    if "walk_forward_metrics" in result:
        _clean_frame(result["walk_forward_metrics"]).to_csv(
            output_dir / "zhu_walkline_strategy_walk_forward_metrics.csv",
            index=False,
            encoding="utf-8-sig",
        )
        _clean_frame(result["walk_forward_reviews"]).to_csv(
            output_dir / "zhu_walkline_strategy_walk_forward_reviews.csv",
            index=False,
            encoding="utf-8-sig",
        )
    summary = result["summary"]
    (output_dir / "zhu_walkline_strategy_experiment_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_strategy_experiment_summary.md").write_text(
        summary_markdown(summary, metrics, quarterly),
        encoding="utf-8",
    )


def summary_markdown(
    summary: dict[str, Any],
    metrics: pd.DataFrame,
    quarterly: pd.DataFrame,
) -> str:
    selected = summary["selection"]["selected_variant"]
    holdout = metrics[
        metrics["split"].eq("holdout")
        & metrics["evaluation_scope"].eq(EVALUATION_SCOPE)
        & metrics["variant"].isin(
            [
                BASELINE_VARIANT,
                selected,
                "SAME_COUNT_TOP_RISE",
                "SAME_COUNT_RANDOM",
            ]
        )
    ].drop_duplicates("variant")
    validation = metrics[
        metrics["split"].eq("validation")
        & metrics["evaluation_scope"].eq(EVALUATION_SCOPE)
        & metrics["cohort_type"].isin(["baseline", "mutation"])
    ]
    selected_quarters = quarterly[
        quarterly["variant"].isin([BASELINE_VARIANT, selected])
        & quarterly["evaluation_scope"].eq(EVALUATION_SCOPE)
    ]
    failure_table = pd.DataFrame(summary.get("top_failure_buckets", []))
    walk_forward_lines: list[str] = []
    if "walk_forward_review" in summary:
        walk_forward = summary["walk_forward_review"]
        walk_forward_lines = [
            "",
            "## Yearly Walk-Forward Replication",
            "",
            _markdown_table(
                pd.DataFrame(walk_forward["folds"]),
                [
                    "fold_id",
                    "selected_variant",
                    "holdout_passed",
                    "selected_holdout_avg_net_return_pct",
                    "baseline_holdout_avg_net_return_pct",
                    "selected_holdout_tail_loss_rate",
                    "baseline_holdout_tail_loss_rate",
                ],
            ),
            "",
            f"- replicated_variant: `{walk_forward['replicated_variant']}`",
            f"- replication_decision: `{walk_forward['replication_decision']}`",
        ]
    lines = [
        "# Zhu Walkline Full Strategy Experiment",
        "",
        "本報告是 shadow observation / evaluator-only 研究，不是買進名單，不是交易指令。",
        "",
        "## Experiment Contract",
        "",
        f"- mode: `{MODE}`",
        "- signal: as-of close after the market closes",
        "- entry: next trading day adjusted open",
        "- exit: as-of plus 20 trading days adjusted close",
        "- primary scope: same-stock 20-trading-day cooldown",
        "- selection: 2025 validation only; 2026 holdout not used for selection",
        "- adjusted OHLCV handles corporate actions; a no-event robustness scope is also exported",
        "",
        "## Validation Comparison",
        "",
        _markdown_table(validation, _metric_columns()),
        "",
        "## Locked Holdout Comparison",
        "",
        _markdown_table(holdout, _metric_columns()),
        "",
        "## Selected Variant Quarterly Stability",
        "",
        _markdown_table(
            selected_quarters,
            [
                "variant",
                "quarter",
                "split",
                "rows",
                "avg_net_return_pct",
                "median_net_return_pct",
                "downside_rate_net_lt_0",
                "tail_loss_rate_net_le_neg10",
            ],
        ),
        "",
        "## Highest Tail-Risk Buckets",
        "",
        _markdown_table(
            failure_table,
            [
                "dimension",
                "bucket",
                "split",
                "feature_timing",
                "rows",
                "avg_net_return_pct",
                "median_net_return_pct",
                "downside_rate_net_lt_0",
                "tail_loss_rate_net_le_neg10",
            ],
        ),
        *walk_forward_lines,
        "",
        "## Research Recommendation",
        "",
        f"- selected_by_validation: `{selected}`",
        f"- promotion_decision: `{summary['promotion_decision']}`",
        f"- reason: {summary['selection']['reason']}",
        f"- holdout: {summary['holdout_review']['reason']}",
        "- post_holdout_risk_candidate: "
        f"`{summary['research_recommendations']['risk_control_candidate']}`",
        "- 上述 risk candidate 是看過 holdout 後的研究線索，只能交給下一輪資料複驗。",
        "- 建議只保留為 shadow/advisory 候選規則，未經另行 promotion review 不得改動正式策略。",
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
    return "\n".join(lines) + "\n"


def _metric_columns() -> list[str]:
    return [
        "variant",
        "rows",
        "unique_stocks",
        "date_count",
        "avg_net_return_pct",
        "median_net_return_pct",
        "daily_equal_weight_avg_net_return_pct",
        "hit_rate_net_ge_20",
        "downside_rate_net_lt_0",
        "tail_loss_rate_net_le_neg10",
        "avg_entry_gap_pct",
    ]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates-csv",
        default=(
            "reports/zhu_walkline_early_observation_labels_2024_2026_06_10/"
            "zhu_walkline_early_observation_candidates.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_strategy_experiment_2024_2026_06_10",
    )
    parser.add_argument(
        "--additional-candidates-csv",
        action="append",
        default=[],
        help="Append another non-overlapping candidate CSV for replication.",
    )
    parser.add_argument(
        "--run-yearly-walk-forward",
        action="store_true",
        help="Run fixed yearly validation-to-holdout replication folds.",
    )
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--horizon-trading-days", type=int, default=20)
    parser.add_argument("--development-end", default="2024-12-31")
    parser.add_argument("--validation-end", default="2025-12-31")
    parser.add_argument("--holdout-end", default="2026-06-10")
    parser.add_argument("--minimum-validation-rows", type=int, default=50)
    parser.add_argument("--minimum-validation-coverage", type=float, default=0.30)
    parser.add_argument("--brokerage-fee-rate", type=float, default=0.001425)
    parser.add_argument("--sell-tax-rate", type=float, default=0.003)
    parser.add_argument("--one-way-slippage-rate", type=float, default=0.001)
    return parser.parse_args(argv)


def _clean_flag(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame.get(column), errors="coerce")
    return values.eq(0.0) & values.notna()


def _evaluation_scope_rows(
    metrics: pd.DataFrame,
    *,
    variant: str,
    split: str,
) -> pd.DataFrame:
    return metrics[
        metrics["variant"].eq(variant)
        & metrics["split"].eq(split)
        & metrics["evaluation_scope"].eq(EVALUATION_SCOPE)
    ]


def _add_empty_execution_columns(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in sorted(EVALUATOR_ONLY_COLUMNS | {"label_mature"}):
        output[column] = pd.NA
    return output


def _latest_adjusted_asof(adjusted_prices: pd.DataFrame) -> str:
    if adjusted_prices.empty or "adjusted_data_asof" not in adjusted_prices:
        return ""
    values = adjusted_prices["adjusted_data_asof"].dropna().astype(str)
    return values.max() if not values.empty else ""


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    selected = frame[[column for column in columns if column in frame.columns]].copy()
    lines = [
        "| " + " | ".join(selected.columns) + " |",
        "| " + " | ".join("---" for _ in selected.columns) + " |",
    ]
    for _, row in selected.iterrows():
        lines.append(
            "| "
            + " | ".join(str(_clean_value(row[column])) for column in selected.columns)
            + " |"
        )
    return "\n".join(lines)


def _round_numeric(frame: pd.DataFrame, decimals: int = 6) -> pd.DataFrame:
    output = frame.copy()
    numeric_columns = output.select_dtypes(include=["number"]).columns
    output[numeric_columns] = output[numeric_columns].round(decimals)
    return output


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.copy().where(pd.notna(frame), "")


def _clean_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return ""
    return value


def _records_for_json(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_record_for_json(row) for row in frame.to_dict("records")]


def _record_for_json(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _json_value(value) for key, value in row.items()}


def _json_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _ge(left: Any, right: Any) -> bool:
    left_value = _float_or(left, float("-inf"))
    right_value = _float_or(right, float("inf"))
    return left_value >= right_value


def _le(left: Any, right: Any) -> bool:
    left_value = _float_or(left, float("inf"))
    right_value = _float_or(right, float("-inf"))
    return left_value <= right_value


def _float_or(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if pd.notna(number) else default


def _nearly_equal(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    return abs(_float_or(left, float("inf")) - _float_or(right, float("-inf"))) <= tolerance


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
