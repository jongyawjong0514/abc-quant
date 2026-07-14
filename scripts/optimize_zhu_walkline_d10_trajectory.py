"""Optimize a full D-10 through D shadow timing trajectory."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from abc_quant.features.early_start_trajectory import (  # noqa: E402
    EarlyTrajectoryRule,
    build_event_trajectory,
    build_relative_day_profile,
    build_t1_baseline_alerts,
    earliest_alert_rows,
    evaluate_event_alerts,
    event_frame_from_trajectory,
    generate_trajectory_rules,
    trajectory_rule_mask,
)
from abc_quant.features.pre_signal_features import (  # noqa: E402
    build_pre_signal_feature_frame,
)
from abc_quant.features.shadow_strength import apply_shadow_strength_score  # noqa: E402
from scripts.analyze_zhu_walkline_kd_d5_lead_snapshots import (  # noqa: E402
    load_adjusted_history,
    prepare_adjusted_history,
)
from scripts.analyze_zhu_walkline_kd_d5_pre_signal_features import (  # noqa: E402
    assert_no_lookahead,
    load_local_histories,
    load_wide_panel,
)
from scripts.optimize_zhu_walkline_early_start_parameters import (  # noqa: E402
    prepare_modeling_events,
)
from scripts.score_zhu_walkline_daily_shadow_strength import (  # noqa: E402
    load_frozen_rules,
)


def run_optimizer(
    *,
    input_csv: Path,
    sqlite_path: Path,
    finlab_root: Path,
    rules_csv: Path,
    config: dict[str, Any],
    output_dir: Path,
    reuse_trajectory: bool = False,
) -> dict[str, Any]:
    """Run the bounded trajectory experiment and archive every artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    trajectory_path = output_dir / "zhu_walkline_d10_trajectory_rows.csv"
    if reuse_trajectory and trajectory_path.exists():
        trajectory = pd.read_csv(
            trajectory_path,
            dtype={"stock_id": str},
            parse_dates=False,
        )
        reuse_validation = _validate_reused_trajectory(
            trajectory,
            input_csv=input_csv,
            config=config,
        )
    else:
        trajectory = _build_scored_trajectory(
            input_csv=input_csv,
            sqlite_path=sqlite_path,
            finlab_root=finlab_root,
            rules_csv=rules_csv,
            config=config,
        )
        reuse_validation = "not_reused"

    trajectory = _attach_event_endpoint_metadata(
        trajectory,
        input_csv=input_csv,
        config=config,
    )
    _safe_csv(trajectory, trajectory_path)

    analysis = config["analysis"]
    trajectory["split"] = _assign_splits(trajectory["signal_date"], analysis)
    trajectory["target_gain_ge10"] = pd.to_numeric(
        trajectory["d5_adjusted_return_pct"], errors="raise"
    ).ge(float(analysis["target_return_pct"]))
    trajectory["target_gain_ge20"] = pd.to_numeric(
        trajectory["d5_adjusted_return_pct"], errors="raise"
    ).ge(float(analysis["large_gain_return_pct"]))
    event_rows = event_frame_from_trajectory(
        trajectory,
        target_return_pct=float(analysis["target_return_pct"]),
        large_gain_return_pct=float(analysis["large_gain_return_pct"]),
    )
    baseline_alerts = build_t1_baseline_alerts(trajectory)
    baseline_metrics = {
        split: evaluate_event_alerts(event_rows, baseline_alerts, split=split)
        for split in ("DISCOVERY", "VALIDATION", "HOLDOUT")
    }
    search, selected_rule, selection_reason = search_rules(
        trajectory,
        event_rows=event_rows,
        baseline_metrics=baseline_metrics,
        search_grid=config["search_grid"],
        analysis_config=analysis,
        selection_config=config["selection"],
    )
    selected_alerts = earliest_alert_rows(
        trajectory,
        trajectory_rule_mask(
            trajectory,
            selected_rule,
            minimum_lead_days=int(analysis["earliest_rule_minimum_lead_days"]),
            maximum_lead_days=int(analysis["earliest_rule_maximum_lead_days"]),
        ),
    )
    selected_metrics = {
        split: evaluate_event_alerts(event_rows, selected_alerts, split=split)
        for split in ("DISCOVERY", "VALIDATION", "HOLDOUT")
    }
    unpurged_validation_pass = _noninferior(
        selected_metrics["VALIDATION"],
        baseline_metrics["VALIDATION"],
        config["selection"],
    )
    unpurged_holdout_pass = (
        _noninferior(
            selected_metrics["HOLDOUT"],
            baseline_metrics["HOLDOUT"],
            config["selection"],
        )
        and selected_metrics["HOLDOUT"]["selected_rows"]
        >= int(config["selection"]["minimum_holdout_rows"])
    )
    purged_stress = build_purged_temporal_stress(
        trajectory,
        event_rows=event_rows,
        baseline_alerts=baseline_alerts,
        selected_alerts=selected_alerts,
    )
    purged_validation_baseline = _purged_metric(
        purged_stress, split="VALIDATION", variant="PRESPECIFIED_T1"
    )
    purged_validation_selected = _purged_metric(
        purged_stress, split="VALIDATION", variant="D10_OPTIMIZED"
    )
    purged_holdout_baseline = _purged_metric(
        purged_stress, split="HOLDOUT", variant="PRESPECIFIED_T1"
    )
    purged_holdout_selected = _purged_metric(
        purged_stress, split="HOLDOUT", variant="D10_OPTIMIZED"
    )
    strict_validation_pass = _noninferior(
        purged_validation_selected,
        purged_validation_baseline,
        config["selection"],
    )
    strict_holdout_pass = (
        _noninferior(
            purged_holdout_selected,
            purged_holdout_baseline,
            config["selection"],
        )
        and purged_holdout_selected["selected_rows"]
        >= int(config["selection"]["minimum_holdout_rows"])
    )
    earlier_accuracy_verified = bool(strict_validation_pass and strict_holdout_pass)
    profile = build_relative_day_profile(trajectory)
    metrics = _metrics_frame(baseline_metrics, selected_metrics)
    monthly = build_holdout_monthly_metrics(
        event_rows,
        baseline_alerts=baseline_alerts,
        selected_alerts=selected_alerts,
    )
    summary = {
        "purpose": "D-10_to_D_earlier_start_observation_optimization",
        "market": "TW",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "signal_start": analysis["signal_start"],
        "signal_end": analysis["signal_end"],
        "target": (
            f"primary continuation label: D close to D+5 adjusted close return >= "
            f"{analysis['target_return_pct']}%; early-entry diagnostic also reports "
            "alert close to the same D+5 endpoint"
        ),
        "event_rows": int(len(event_rows)),
        "trajectory_rows": int(len(trajectory)),
        "relative_days": [
            f"D-{value}"
            for value in range(
                int(analysis["maximum_lead_trading_days"]), 0, -1
            )
        ]
        + ["D"],
        "search_candidates": int(len(search)),
        "selected_rule": asdict(selected_rule),
        "selection_reason": selection_reason,
        "validation_noninferiority_pass": bool(strict_validation_pass),
        "holdout_noninferiority_pass": bool(strict_holdout_pass),
        "unpurged_validation_noninferiority_pass": bool(
            unpurged_validation_pass
        ),
        "unpurged_holdout_noninferiority_pass": bool(unpurged_holdout_pass),
        "strict_purged_validation_noninferiority_pass": bool(
            strict_validation_pass
        ),
        "strict_purged_holdout_noninferiority_pass": bool(strict_holdout_pass),
        "earlier_accuracy_verified": earlier_accuracy_verified,
        "purged_temporal_stress": _json_safe(
            purged_stress[
                [
                    "variant",
                    "split",
                    "prior_label_freeze_date",
                    "original_split_rows",
                    "purged_split_rows",
                    "removed_rows",
                    "selected_rows",
                    "precision_gain_ge10",
                    "recall_gain_ge10",
                    "balanced_accuracy_gain_ge10",
                    "loss_rate",
                    "median_lead_days",
                    "gain_ge10_from_alert_to_d5_rate",
                    "median_alert_to_d5_adjusted_return_pct",
                ]
            ].to_dict(orient="records")
        ),
        "temporal_evaluation": (
            "rule selection archive is unpurged and exploratory; final verification uses "
            "a strict label-maturity purge where every D-10 window begins after all prior "
            "split D+5 labels are available"
        ),
        "reuse_validation": reuse_validation,
        "weakest_error_class": (
            "signal-day confirmation occurs after a large D-day price expansion; earlier "
            "rules risk low precision and event-conditioned membership leakage"
        ),
        "four_component_role": (
            "reported for every relative day using strictly prior component dates; frozen "
            "score is not used to tune the technical timing rule"
        ),
        "no_lookahead": (
            "technical fields use observation_date or earlier; four-component source dates "
            "are strictly before observation_date; D+5 outcomes are evaluator-only"
        ),
        "corporate_action_adjustment": (
            "mature D+5 labels use adjusted close; events with corporate actions in the "
            "forward horizon are excluded"
        ),
        "cost_slippage_liquidity": (
            "observation-classification study only; no order or return backtest, so costs "
            "and slippage are not applied; scanner membership supplies the research universe"
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
        "trajectory": trajectory,
        "profile": profile,
        "search": search,
        "metrics": metrics,
        "monthly": monthly,
        "purged_stress": purged_stress,
        "selected_alerts": selected_alerts,
        "baseline_alerts": baseline_alerts,
        "summary": summary,
    }
    write_outputs(result, output_dir=output_dir)
    return result


def search_rules(
    trajectory: pd.DataFrame,
    *,
    event_rows: pd.DataFrame,
    baseline_metrics: dict[str, dict[str, Any]],
    search_grid: dict[str, list[float]],
    analysis_config: dict[str, Any],
    selection_config: dict[str, Any],
) -> tuple[pd.DataFrame, EarlyTrajectoryRule, str]:
    """Rank on discovery and use validation only as a non-regression gate."""
    records: list[dict[str, Any]] = []
    rules: dict[int, EarlyTrajectoryRule] = {}
    for candidate_id, rule in enumerate(generate_trajectory_rules(search_grid)):
        rules[candidate_id] = rule
        mask = trajectory_rule_mask(
            trajectory,
            rule,
            minimum_lead_days=int(analysis_config["earliest_rule_minimum_lead_days"]),
            maximum_lead_days=int(analysis_config["earliest_rule_maximum_lead_days"]),
        )
        alerts = earliest_alert_rows(trajectory, mask)
        discovery = evaluate_event_alerts(event_rows, alerts, split="DISCOVERY")
        validation = evaluate_event_alerts(event_rows, alerts, split="VALIDATION")
        eligible = (
            discovery["selected_rows"]
            >= int(selection_config["minimum_discovery_rows"])
            and validation["selected_rows"]
            >= int(selection_config["minimum_validation_rows"])
            and (
                not bool(selection_config["require_all_months_nonempty"])
                or discovery["empty_months"] == validation["empty_months"] == 0
            )
        )
        validation_pass = eligible and _noninferior(
            validation,
            baseline_metrics["VALIDATION"],
            selection_config,
        )
        record = {
            "candidate_id": candidate_id,
            **rule.to_dict(),
            "eligible": eligible,
            "validation_nonregression_pass": validation_pass,
            "discovery_score": _discovery_score(discovery),
        }
        record.update(_prefixed(discovery, "discovery"))
        record.update(_prefixed(validation, "validation"))
        records.append(record)
    search = pd.DataFrame(records).sort_values(
        ["eligible", "discovery_score", "candidate_id"],
        ascending=[False, False, True],
    )
    shortlist = search[search["eligible"]].head(
        int(selection_config["discovery_shortlist_size"])
    )
    accepted = shortlist[shortlist["validation_nonregression_pass"]]
    if not accepted.empty:
        selected_id = int(accepted.iloc[0]["candidate_id"])
        reason = "DISCOVERY_RANKED_VALIDATION_PASS"
    elif not shortlist.empty:
        selected_id = int(shortlist.iloc[0]["candidate_id"])
        reason = "DIAGNOSTIC_ONLY_NO_VALIDATION_NONINFERIOR_RULE"
    else:
        selected_id = int(search.iloc[0]["candidate_id"])
        reason = "DIAGNOSTIC_ONLY_NO_ELIGIBLE_RULE"
    return search.reset_index(drop=True), rules[selected_id], reason


def build_holdout_monthly_metrics(
    event_rows: pd.DataFrame,
    *,
    baseline_alerts: pd.DataFrame,
    selected_alerts: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate May and June separately after rules are frozen."""
    records: list[dict[str, Any]] = []
    holdout = event_rows[event_rows["split"].eq("HOLDOUT")].copy()
    holdout["month"] = pd.to_datetime(holdout["signal_date"]).dt.to_period("M").astype(str)
    for month in sorted(holdout["month"].unique()):
        month_events = holdout[holdout["month"].eq(month)].copy()
        month_events["split"] = "MONTH"
        for variant, alerts in {
            "PRESPECIFIED_T1": baseline_alerts,
            "D10_OPTIMIZED": selected_alerts,
        }.items():
            records.append(
                {
                    "month": month,
                    "variant": variant,
                    **evaluate_event_alerts(month_events, alerts, split="MONTH"),
                }
            )
    return pd.DataFrame(records)


def build_purged_temporal_stress(
    trajectory: pd.DataFrame,
    *,
    event_rows: pd.DataFrame,
    baseline_alerts: pd.DataFrame,
    selected_alerts: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate frozen alerts after prior-split D+5 labels have fully matured."""
    required = {"signal_date", "stock_id", "observation_date", "lead_days"}
    missing = required - set(trajectory.columns)
    if missing:
        raise ValueError(f"trajectory missing purge columns: {sorted(missing)}")
    if "d5_close_date" not in event_rows:
        raise ValueError("event rows require d5_close_date for temporal purge")

    earliest = (
        trajectory.sort_values("lead_days", ascending=False)
        .drop_duplicates(["signal_date", "stock_id"], keep="first")
        [["signal_date", "stock_id", "observation_date"]]
        .rename(columns={"observation_date": "earliest_observation_date"})
    )
    events = event_rows.merge(
        earliest,
        on=["signal_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    events["d5_close_date"] = pd.to_datetime(events["d5_close_date"], errors="raise")
    events["earliest_observation_date"] = pd.to_datetime(
        events["earliest_observation_date"], errors="raise"
    )

    records: list[dict[str, Any]] = []
    for split, prior_split in (
        ("VALIDATION", "DISCOVERY"),
        ("HOLDOUT", "VALIDATION"),
    ):
        prior = events[events["split"].eq(prior_split)]
        freeze_date = prior["d5_close_date"].max()
        if pd.isna(freeze_date):
            raise ValueError(f"no {prior_split} D+5 close date for temporal purge")
        original = events[events["split"].eq(split)].copy()
        purged = original[
            original["earliest_observation_date"].gt(freeze_date)
        ].copy()
        for variant, alerts in {
            "PRESPECIFIED_T1": baseline_alerts,
            "D10_OPTIMIZED": selected_alerts,
        }.items():
            metric = evaluate_event_alerts(purged, alerts, split=split)
            records.append(
                {
                    "evaluation_scope": "strict_label_maturity_purged",
                    "variant": variant,
                    "prior_label_split": prior_split,
                    "prior_label_freeze_date": pd.Timestamp(freeze_date).strftime(
                        "%Y-%m-%d"
                    ),
                    "original_split_rows": int(len(original)),
                    "purged_split_rows": int(len(purged)),
                    "removed_rows": int(len(original) - len(purged)),
                    **metric,
                }
            )
    return pd.DataFrame(records)


def _purged_metric(
    rows: pd.DataFrame,
    *,
    split: str,
    variant: str,
) -> dict[str, Any]:
    selected = rows[rows["split"].eq(split) & rows["variant"].eq(variant)]
    if len(selected) != 1:
        raise ValueError(f"expected one purged metric for {split}/{variant}")
    return selected.iloc[0].to_dict()


def _prepare_endpoint_events(
    input_csv: Path,
    *,
    config: dict[str, Any],
) -> pd.DataFrame:
    analysis = config["analysis"]
    raw = pd.read_csv(input_csv, dtype={"stock_id": str})
    events = prepare_modeling_events(
        raw,
        signal_start=analysis["signal_start"],
        signal_end=analysis["signal_end"],
        cooldown_trade_days=int(analysis["same_stock_cooldown_trade_days"]),
    )
    required = {
        "asof_date",
        "stock_id",
        "d5_close_date",
        "d5_adj_close",
        "signal_adj_close",
    }
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"events missing endpoint columns: {sorted(missing)}")
    output = events[
        [
            "asof_date",
            "stock_id",
            "d5_close_date",
            "d5_adj_close",
            "signal_adj_close",
        ]
    ].copy()
    output = output.rename(columns={"asof_date": "signal_date"})
    output["signal_date"] = pd.to_datetime(
        output["signal_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    output["d5_close_date"] = pd.to_datetime(
        output["d5_close_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    return output


def _attach_event_endpoint_metadata(
    trajectory: pd.DataFrame,
    *,
    input_csv: Path,
    config: dict[str, Any],
) -> pd.DataFrame:
    endpoints = _prepare_endpoint_events(input_csv, config=config)
    output = trajectory.copy()
    output["signal_date"] = pd.to_datetime(
        output["signal_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    endpoint_columns = ["d5_close_date", "d5_adj_close", "signal_adj_close"]
    output = output.drop(columns=endpoint_columns, errors="ignore").merge(
        endpoints,
        on=["signal_date", "stock_id"],
        how="left",
        validate="many_to_one",
    )
    if output[endpoint_columns].isna().any(axis=None):
        raise ValueError("trajectory endpoint metadata is incomplete")
    return output


def _validate_reused_trajectory(
    trajectory: pd.DataFrame,
    *,
    input_csv: Path,
    config: dict[str, Any],
) -> str:
    required = {
        "signal_date",
        "observation_date",
        "stock_id",
        "lead_days",
        "shadow_strength_score_version",
    }
    missing = required - set(trajectory.columns)
    if missing:
        raise ValueError(f"reused trajectory missing columns: {sorted(missing)}")
    endpoints = _prepare_endpoint_events(input_csv, config=config)
    expected_keys = set(
        endpoints[["signal_date", "stock_id"]].astype(str).agg("|".join, axis=1)
    )
    d_rows = trajectory[pd.to_numeric(trajectory["lead_days"], errors="raise").eq(0)]
    actual_keys = set(
        d_rows[["signal_date", "stock_id"]].astype(str).agg("|".join, axis=1)
    )
    if actual_keys != expected_keys:
        raise ValueError("reused trajectory event keys do not match current input")
    maximum_lead = int(config["analysis"]["maximum_lead_trading_days"])
    counts = trajectory.groupby(["signal_date", "stock_id"])["lead_days"].agg(
        ["count", "min", "max"]
    )
    valid_grid = (
        counts["count"].eq(maximum_lead + 1)
        & counts["min"].eq(0)
        & counts["max"].eq(maximum_lead)
    )
    if not valid_grid.all():
        raise ValueError("reused trajectory does not match configured lead grid")
    return "event_keys_and_lead_grid_validated"


def write_outputs(result: dict[str, Any], *, output_dir: Path) -> None:
    _safe_csv(result["trajectory"], output_dir / "zhu_walkline_d10_trajectory_rows.csv")
    _safe_csv(result["profile"], output_dir / "zhu_walkline_d10_relative_day_profile.csv")
    _safe_csv(result["search"], output_dir / "zhu_walkline_d10_parameter_search.csv")
    _safe_csv(result["metrics"], output_dir / "zhu_walkline_d10_split_metrics.csv")
    _safe_csv(result["monthly"], output_dir / "zhu_walkline_d10_holdout_monthly.csv")
    _safe_csv(
        result["purged_stress"],
        output_dir / "zhu_walkline_d10_purged_temporal_stress.csv",
    )
    _safe_csv(result["selected_alerts"], output_dir / "zhu_walkline_d10_selected_alerts.csv")
    _safe_csv(result["baseline_alerts"], output_dir / "zhu_walkline_d10_t1_baseline_alerts.csv")
    (output_dir / "zhu_walkline_d10_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_d10_summary.md").write_text(
        render_markdown(result),
        encoding="utf-8",
    )


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    metrics = result["metrics"]
    holdout = metrics[metrics["split"].eq("HOLDOUT")]
    purged = result["purged_stress"]
    lines = [
        "# Zhu Walkline D-10～D 提早起漲觀察最佳化",
        "",
        "## 結論",
        "",
        f"- 是否在未見樣本驗證更早且維持準確度：`{summary['earlier_accuracy_verified']}`",
        f"- 選定技術規則：`{json.dumps(summary['selected_rule'], ensure_ascii=False)}`",
        f"- 選擇狀態：`{summary['selection_reason']}`。",
        "- 四項影子強度逐日顯示，但不參與本輪技術門檻調參。",
        "- 研究母體事後以 D 日確認事件組成，因此不得直接當成 live 全市場早期選股器。",
        "- 最終判定使用 label-maturity purge；未 purge 的時間留出只保留為探索性對照。",
        "",
        "## 設計",
        "",
        f"- 事件：{summary['event_rows']}；D-10～D 軌跡列：{summary['trajectory_rows']}。",
        "- discovery=2026-01～02；validation=2026-03～04；holdout=2026-05～06。",
        f"- 搜尋 {summary['search_candidates']} 組有界規則；D+5 結果只供 evaluator。",
        "- 排除 forward corporate-action 事件並使用 adjusted-close 標籤。",
        "",
        "## 2026-05～06 時間留出（未 purge，已查看）",
        "",
        "| 變體 | 筆數 | D→D+5 >=10%精確率 | 召回率 | 平衡準確率 | D→D+5虧損率 | 中位提前日 | 提醒→D中位漲幅 | 提醒→D+5 >=10% | 提醒→D+5中位回報 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in holdout.itertuples():
        lines.append(
            f"| {row.variant} | {row.selected_rows} | {row.precision_gain_ge10:.2%} | "
            f"{row.recall_gain_ge10:.2%} | {row.balanced_accuracy_gain_ge10:.2%} | "
            f"{row.loss_rate:.2%} | {row.median_lead_days:.1f} | "
            f"{row.median_alert_to_signal_return_pct:.2f}% | "
            f"{row.gain_ge10_from_alert_to_d5_rate:.2%} | "
            f"{row.median_alert_to_d5_adjusted_return_pct:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## 嚴格時間 purge 壓力測試",
            "",
            "每一段的 D-10 起點必須晚於前一段所有 D+5 標籤成熟日；規則固定，不重新搜尋。",
            "",
            "| 分段 | 前段標籤凍結日 | 變體 | 保留事件 | 提醒數 | D→D+5精確率 | 召回率 | 平衡準確率 | D→D+5虧損率 | 中位提前日 | 提醒→D+5 >=10% | 提醒→D+5中位回報 |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in purged.itertuples():
        lines.append(
            f"| {row.split} | {row.prior_label_freeze_date} | {row.variant} | "
            f"{row.purged_split_rows} | {row.selected_rows} | "
            f"{row.precision_gain_ge10:.2%} | {row.recall_gain_ge10:.2%} | "
            f"{row.balanced_accuracy_gain_ge10:.2%} | {row.loss_rate:.2%} | "
            f"{row.median_lead_days:.1f} | "
            f"{row.gain_ge10_from_alert_to_d5_rate:.2%} | "
            f"{row.median_alert_to_d5_adjusted_return_pct:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## 治理邊界",
            "",
            f"- `research_scope={summary['research_scope']}`",
            f"- `live_deployable={summary['live_deployable']}`",
            f"- `next_required_gate={summary['next_required_gate']}`",
            f"- `promotion_decision={summary['promotion_decision']}`",
            "- `formal_champion_changed=False`",
            "- `formal_trade_effect=False`",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_scored_trajectory(
    *,
    input_csv: Path,
    sqlite_path: Path,
    finlab_root: Path,
    rules_csv: Path,
    config: dict[str, Any],
) -> pd.DataFrame:
    analysis = config["analysis"]
    raw = pd.read_csv(input_csv, dtype={"stock_id": str})
    events = prepare_modeling_events(
        raw,
        signal_start=analysis["signal_start"],
        signal_end=analysis["signal_end"],
        cooldown_trade_days=int(analysis["same_stock_cooldown_trade_days"]),
    )
    adjusted = load_adjusted_history(
        sqlite_path,
        stock_ids=sorted(events["stock_id"].unique()),
        start_date=(events["asof_date"].min() - pd.Timedelta(days=500)).date().isoformat(),
        end_date=events["asof_date"].max().date().isoformat(),
    )
    feature_history = prepare_adjusted_history(adjusted)
    trajectory = build_event_trajectory(
        events,
        feature_history,
        maximum_lead_days=int(analysis["maximum_lead_trading_days"]),
    )
    keys = (
        trajectory[["observation_date", "stock_id"]]
        .rename(columns={"observation_date": "asof_date"})
        .drop_duplicates()
    )
    stock_ids = sorted(keys["stock_id"].unique())
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
        price_history=histories["price"],
        institutional_history=histories["institutional"],
        holder_history=histories["holder"],
        margin_history=histories["margin"],
        main_force_panel=main_force,
        broker_count_panel=broker_count,
    )
    assert_no_lookahead(features)
    strength = apply_shadow_strength_score(
        features,
        rules=load_frozen_rules(rules_csv),
    )
    strength = strength.rename(columns={"asof_date": "observation_date"})
    return trajectory.merge(
        strength,
        on=["observation_date", "stock_id"],
        how="left",
        validate="many_to_one",
    )


def _metrics_frame(
    baseline: dict[str, dict[str, Any]],
    selected: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for variant, metrics in {
        "PRESPECIFIED_T1": baseline,
        "D10_OPTIMIZED": selected,
    }.items():
        for split, values in metrics.items():
            records.append({"variant": variant, **values})
    return pd.DataFrame(records)


def _assign_splits(values: pd.Series, config: dict[str, Any]) -> pd.Series:
    dates = pd.to_datetime(values, errors="raise")
    output = pd.Series("OUT_OF_SCOPE", index=values.index, dtype="string")
    for split, start_key, end_key in [
        ("DISCOVERY", "discovery_start", "discovery_end"),
        ("VALIDATION", "validation_start", "validation_end"),
        ("HOLDOUT", "holdout_start", "holdout_end"),
    ]:
        output.loc[dates.between(pd.Timestamp(config[start_key]), pd.Timestamp(config[end_key]))] = split
    if output.eq("OUT_OF_SCOPE").any():
        raise ValueError("trajectory contains rows outside configured temporal splits")
    return output


def _noninferior(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    checks = [
        candidate["precision_gain_ge10"]
        >= reference["precision_gain_ge10"]
        - float(config["precision_noninferiority_margin"]),
        candidate["balanced_accuracy_gain_ge10"]
        >= reference["balanced_accuracy_gain_ge10"]
        - float(config["balanced_accuracy_noninferiority_margin"]),
        candidate["loss_rate"]
        <= reference["loss_rate"] + float(config["loss_rate_tolerance"]),
    ]
    if bool(config["require_recall_nonregression"]):
        checks.append(candidate["recall_gain_ge10"] >= reference["recall_gain_ge10"])
    if bool(config["require_all_months_nonempty"]):
        checks.append(candidate["empty_months"] == 0)
    return all(bool(value) for value in checks)


def _discovery_score(metrics: dict[str, Any]) -> float:
    return float(
        0.40 * metrics["precision_lift_vs_all"]
        + 0.20 * metrics["balanced_accuracy_gain_ge10"]
        + 0.20 * metrics["f1_gain_ge10"]
        + 0.10 * metrics["recall_gain_ge10"]
        + 0.10 * min(metrics["median_lead_days"], 10.0) / 10.0
    )


def _prefixed(values: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in values.items() if key != "split"}


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


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        default=(
            "reports/zhu_walkline_kd_d5_groups_2026_01_06/"
            "zhu_walkline_kd_d5_labeled_rows.csv"
        ),
    )
    parser.add_argument("--config", default="config/zhu_walkline_d10_trajectory_optimizer.yaml")
    parser.add_argument("--rules-csv", default="config/zhu_walkline_shadow_strength_rules.csv")
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_d10_trajectory_optimizer_2026_01_06",
    )
    parser.add_argument("--reuse-trajectory", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    experiment = _load_yaml(_repo_path(args.config))
    scanner = _load_yaml(REPO_ROOT / "config/zhu_walkline_shadow.yaml")
    result = run_optimizer(
        input_csv=_repo_path(args.input_csv),
        sqlite_path=Path(scanner["data"]["sqlite_path"]),
        finlab_root=Path(scanner["data"]["finlab_items_root"]),
        rules_csv=_repo_path(args.rules_csv),
        config=experiment,
        output_dir=_repo_path(args.output_dir),
        reuse_trajectory=bool(args.reuse_trajectory),
    )
    summary = result["summary"]
    print(f"event_rows={summary['event_rows']}")
    print(f"trajectory_rows={summary['trajectory_rows']}")
    print(f"search_candidates={summary['search_candidates']}")
    print(f"earlier_accuracy_verified={summary['earlier_accuracy_verified']}")
    print(f"live_deployable={summary['live_deployable']}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
