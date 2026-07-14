"""Tune bounded T-5/T-3/T-1 shadow observation parameters without lookahead.

The search uses January-February 2026 for discovery, March-April for
validation, and opens May-June exactly once as the final holdout.  It is a
research sidecar and never changes the formal champion or trading behavior.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_zhu_walkline_kd_d5_lead_snapshots import (  # noqa: E402
    build_lead_snapshots,
    load_adjusted_history,
)


STAGES = ("T5_SETUP", "T3_EARLY_TURN", "T1_PRICE_VOLUME_CONFIRM")
LEAD_BY_STAGE = {
    "T5_SETUP": 5,
    "T3_EARLY_TURN": 3,
    "T1_PRICE_VOLUME_CONFIRM": 1,
}
MODEL_FEATURES = (
    "day_volume_ratio_20",
    "daily_return_pct",
    "kd_k_change_1d",
    "sma20_slope_5d_pct",
    "close_to_sma20_pct",
)


@dataclass(frozen=True)
class EarlyStartParameters:
    """One point-in-time stage rule from the bounded search space."""

    stage: str
    t5_volume_ratio_max: float = 0.75
    t5_require_positive_ma20_slope: bool = False
    t3_daily_return_min_pct: float | None = None
    t3_k_change_min: float | None = None
    t1_daily_return_min_pct: float | None = None
    t1_volume_ratio_min: float | None = None
    t1_require_above_ma20: bool = False

    @property
    def lead_trading_days(self) -> int:
        return LEAD_BY_STAGE[self.stage]

    @property
    def complexity(self) -> int:
        return int(self.t5_require_positive_ma20_slope) + int(
            self.t3_k_change_min is not None
        ) + int(self.t1_require_above_ma20)


def apply_same_stock_cooldown(
    rows: pd.DataFrame,
    *,
    minimum_trade_days: int = 5,
) -> pd.DataFrame:
    """De-overlap signals using only signal date, stock, and trade index."""
    required = {"asof_date", "stock_id", "signal_trade_index"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"signal rows missing cooldown columns: {sorted(missing)}")
    output = rows.copy()
    output["asof_date"] = pd.to_datetime(output["asof_date"], errors="raise")
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["signal_trade_index"] = pd.to_numeric(
        output["signal_trade_index"], errors="raise"
    )
    output = output.sort_values(["stock_id", "asof_date"]).copy()
    keep: list[bool] = []
    last_kept_index: dict[str, float] = {}
    for row in output.itertuples(index=False):
        stock_id = str(row.stock_id)
        trade_index = float(row.signal_trade_index)
        prior = last_kept_index.get(stock_id)
        accepted = prior is None or trade_index - prior >= minimum_trade_days
        keep.append(accepted)
        if accepted:
            last_kept_index[stock_id] = trade_index
    output["same_stock_cooldown"] = keep
    return output


def prepare_modeling_events(
    rows: pd.DataFrame,
    *,
    signal_start: str,
    signal_end: str,
    cooldown_trade_days: int,
) -> pd.DataFrame:
    """Keep complete mature labels after outcome-independent de-overlap."""
    required = {
        "asof_date",
        "d5_close_date",
        "stock_id",
        "stock_name",
        "signal_trade_index",
        "label_mature",
        "corporate_action_event_in_horizon",
        "d5_adjusted_return_pct",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"labeled rows missing required columns: {sorted(missing)}")
    events = rows.copy()
    events["asof_date"] = pd.to_datetime(events["asof_date"], errors="raise")
    events["d5_close_date"] = pd.to_datetime(
        events["d5_close_date"], errors="raise"
    )
    events["stock_id"] = events["stock_id"].astype(str).str.zfill(4)
    events = events[
        events["asof_date"].between(pd.Timestamp(signal_start), pd.Timestamp(signal_end))
    ].copy()
    if events.duplicated(["asof_date", "stock_id"]).any():
        raise ValueError("duplicate signal-date/stock keys")
    events = apply_same_stock_cooldown(
        events,
        minimum_trade_days=cooldown_trade_days,
    )
    mature = _as_bool(events["label_mature"])
    corporate_action = _as_bool(events["corporate_action_event_in_horizon"])
    returns = pd.to_numeric(events["d5_adjusted_return_pct"], errors="coerce")
    events = events[
        mature & ~corporate_action & returns.notna() & events["same_stock_cooldown"]
    ].copy()
    events["d5_adjusted_return_pct"] = returns.loc[events.index]
    events["d5_group"] = events.get("d5_group", pd.Series(index=events.index)).fillna(
        "D5_NEUTRAL_0_10"
    )
    events["d5_group_label"] = events.get(
        "d5_group_label", pd.Series(index=events.index)
    ).fillna("D+5 0% to <10%")
    return events.sort_values(["asof_date", "stock_id"]).reset_index(drop=True)


def build_modeling_matrix(
    events: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    split_config: dict[str, Any],
) -> pd.DataFrame:
    """Pivot exact pre-signal snapshots into one audit row per event."""
    snapshots = snapshots.copy()
    snapshots["asof_date"] = pd.to_datetime(
        snapshots["asof_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    pivot = snapshots.pivot(
        index=["asof_date", "stock_id"],
        columns="lead_offset",
        values=list(MODEL_FEATURES),
    )
    event_meta = events.copy()
    event_meta["asof_date"] = event_meta["asof_date"].dt.strftime("%Y-%m-%d")
    event_meta = event_meta.set_index(["asof_date", "stock_id"])
    if not pivot.index.equals(event_meta.index):
        event_meta = event_meta.reindex(pivot.index)
    matrix = pd.DataFrame(index=pivot.index)
    matrix["stock_name"] = event_meta["stock_name"]
    matrix["d5_adjusted_return_pct"] = pd.to_numeric(
        event_meta["d5_adjusted_return_pct"], errors="raise"
    )
    matrix["d5_close_date"] = pd.to_datetime(
        event_meta["d5_close_date"], errors="raise"
    )
    for feature in MODEL_FEATURES:
        for offset in (5, 3, 1):
            matrix[f"t{offset}_{feature}"] = pd.to_numeric(
                pivot[(feature, offset)], errors="coerce"
            )
    matrix = matrix.reset_index()
    matrix["asof_date"] = pd.to_datetime(matrix["asof_date"], errors="raise")
    matrix["target_gain_ge10"] = matrix["d5_adjusted_return_pct"].ge(
        float(split_config["target_return_pct"])
    )
    matrix["target_gain_ge20"] = matrix["d5_adjusted_return_pct"].ge(
        float(split_config["large_gain_return_pct"])
    )
    matrix["target_loss"] = matrix["d5_adjusted_return_pct"].lt(0)
    matrix["split"] = _assign_splits(
        matrix["asof_date"], matrix["d5_close_date"], split_config
    )
    if matrix["split"].eq("OUT_OF_SCOPE").any():
        raise ValueError("modeling rows fall outside configured temporal splits")
    purged_rows = int(matrix["split"].eq("PURGED_LABEL_BOUNDARY").sum())
    matrix = matrix[~matrix["split"].eq("PURGED_LABEL_BOUNDARY")].copy()
    output = matrix.sort_values(["asof_date", "stock_id"]).reset_index(drop=True)
    output.attrs["purged_label_boundary_rows"] = purged_rows
    return output


def generate_candidates(
    stage: str,
    search_grid: dict[str, list[Any]],
) -> Iterable[EarlyStartParameters]:
    """Generate only parameters used by the requested stage."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    for volume_max in search_grid["t5_volume_ratio_max"]:
        for require_slope in search_grid["t5_require_positive_ma20_slope"]:
            if stage == "T5_SETUP":
                yield EarlyStartParameters(
                    stage=stage,
                    t5_volume_ratio_max=float(volume_max),
                    t5_require_positive_ma20_slope=bool(require_slope),
                )
                continue
            for t3_return in search_grid["t3_daily_return_min_pct"]:
                for k_change in search_grid["t3_k_change_min"]:
                    common = {
                        "stage": stage,
                        "t5_volume_ratio_max": float(volume_max),
                        "t5_require_positive_ma20_slope": bool(require_slope),
                        "t3_daily_return_min_pct": float(t3_return),
                        "t3_k_change_min": None
                        if k_change is None
                        else float(k_change),
                    }
                    if stage == "T3_EARLY_TURN":
                        yield EarlyStartParameters(**common)
                        continue
                    for t1_return in search_grid["t1_daily_return_min_pct"]:
                        for t1_volume in search_grid["t1_volume_ratio_min"]:
                            for require_ma20 in search_grid[
                                "t1_require_above_ma20"
                            ]:
                                yield EarlyStartParameters(
                                    **common,
                                    t1_daily_return_min_pct=float(t1_return),
                                    t1_volume_ratio_min=float(t1_volume),
                                    t1_require_above_ma20=bool(require_ma20),
                                )


def parameter_mask(
    rows: pd.DataFrame,
    parameters: EarlyStartParameters,
) -> pd.Series:
    """Apply one parameter set using only its permitted pre-signal columns."""
    mask = rows["t5_day_volume_ratio_20"].le(parameters.t5_volume_ratio_max)
    if parameters.t5_require_positive_ma20_slope:
        mask &= rows["t5_sma20_slope_5d_pct"].gt(0)
    if parameters.stage in {"T3_EARLY_TURN", "T1_PRICE_VOLUME_CONFIRM"}:
        mask &= rows["t3_daily_return_pct"].gt(parameters.t3_daily_return_min_pct)
        if parameters.t3_k_change_min is not None:
            mask &= rows["t3_kd_k_change_1d"].gt(parameters.t3_k_change_min)
    if parameters.stage == "T1_PRICE_VOLUME_CONFIRM":
        mask &= rows["t1_daily_return_pct"].gt(parameters.t1_daily_return_min_pct)
        mask &= rows["t1_day_volume_ratio_20"].ge(parameters.t1_volume_ratio_min)
        if parameters.t1_require_above_ma20:
            mask &= rows["t1_close_to_sma20_pct"].ge(0)
    return mask.fillna(False)


def classification_metrics(
    rows: pd.DataFrame,
    selected: pd.Series,
    *,
    split: str,
) -> dict[str, Any]:
    """Evaluate the selected observation flag over one temporal split."""
    scope = rows["split"].eq(split)
    actual = rows.loc[scope, "target_gain_ge10"].astype(bool)
    predicted = selected.loc[scope].astype(bool)
    selected_rows = rows.loc[scope & selected]
    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())
    tn = int((~predicted & ~actual).sum())
    precision = _divide(tp, tp + fp)
    recall = _divide(tp, tp + fn)
    specificity = _divide(tn, tn + fp)
    f1 = _divide(2 * precision * recall, precision + recall)
    accuracy = _divide(tp + tn, len(actual))
    balanced_accuracy = (recall + specificity) / 2.0
    split_rows = rows.loc[scope]
    base_precision = float(split_rows["target_gain_ge10"].mean())
    selected_months = int(selected_rows["asof_date"].dt.to_period("M").nunique())
    total_months = int(split_rows["asof_date"].dt.to_period("M").nunique())
    returns = selected_rows["d5_adjusted_return_pct"]
    return {
        "split": split,
        "split_rows": int(len(split_rows)),
        "selected_rows": int(len(selected_rows)),
        "unique_stocks": int(selected_rows["stock_id"].nunique()),
        "selected_months": selected_months,
        "total_months": total_months,
        "empty_months": total_months - selected_months,
        "coverage": _divide(len(selected_rows), len(split_rows)),
        "gain_ge10_rows": tp,
        "precision_gain_ge10": precision,
        "recall_gain_ge10": recall,
        "f1_gain_ge10": f1,
        "specificity_gain_ge10": specificity,
        "accuracy_gain_ge10": accuracy,
        "balanced_accuracy_gain_ge10": balanced_accuracy,
        "precision_lift_vs_all": _divide(precision, base_precision),
        "gain_ge20_rate": float(selected_rows["target_gain_ge20"].mean())
        if len(selected_rows)
        else 0.0,
        "loss_rate": float(selected_rows["target_loss"].mean())
        if len(selected_rows)
        else 0.0,
        "avg_d5_adjusted_return_pct": float(returns.mean())
        if len(selected_rows)
        else 0.0,
        "median_d5_adjusted_return_pct": float(returns.median())
        if len(selected_rows)
        else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def discovery_score(metrics: dict[str, Any], parameters: EarlyStartParameters) -> float:
    """Rank candidates on discovery only with a small complexity penalty."""
    return float(
        0.45 * metrics["precision_lift_vs_all"]
        + 0.25 * metrics["balanced_accuracy_gain_ge10"]
        + 0.20 * metrics["f1_gain_ge10"]
        + 0.10 * metrics["recall_gain_ge10"]
        - 0.015 * parameters.complexity
    )


def search_stage(
    rows: pd.DataFrame,
    *,
    stage: str,
    search_grid: dict[str, list[Any]],
    selection_config: dict[str, Any],
) -> tuple[pd.DataFrame, EarlyStartParameters, str]:
    """Search discovery, then use validation only as a non-regression gate."""
    records: list[dict[str, Any]] = []
    parameters_by_id: dict[int, EarlyStartParameters] = {}
    minimum_rows = int(selection_config["minimum_rows"][stage])
    require_all_months = bool(selection_config["require_all_months_nonempty"])
    default = default_parameters(stage)
    default_validation = classification_metrics(
        rows,
        parameter_mask(rows, default),
        split="VALIDATION",
    )
    for candidate_id, parameters in enumerate(generate_candidates(stage, search_grid)):
        parameters_by_id[candidate_id] = parameters
        mask = parameter_mask(rows, parameters)
        discovery = classification_metrics(rows, mask, split="DISCOVERY")
        validation = classification_metrics(rows, mask, split="VALIDATION")
        eligible = (
            discovery["selected_rows"] >= minimum_rows
            and validation["selected_rows"] >= minimum_rows
            and (
                not require_all_months
                or (
                    discovery["empty_months"] == 0
                    and validation["empty_months"] == 0
                )
            )
        )
        validation_pass = eligible and _noninferior(
            validation,
            default_validation,
            selection_config,
            require_recall=False,
        )
        record: dict[str, Any] = {
            "candidate_id": candidate_id,
            **asdict(parameters),
            "lead_trading_days": parameters.lead_trading_days,
            "complexity": parameters.complexity,
            "eligible": eligible,
            "validation_nonregression_pass": validation_pass,
            "discovery_score": discovery_score(discovery, parameters),
        }
        record.update(_prefixed(discovery, "discovery"))
        record.update(_prefixed(validation, "validation"))
        records.append(record)
    search = pd.DataFrame(records).sort_values(
        ["eligible", "discovery_score", "candidate_id"],
        ascending=[False, False, True],
    )
    shortlist_size = int(selection_config["discovery_shortlist_size"])
    shortlist = search[search["eligible"]].head(shortlist_size)
    accepted = shortlist[shortlist["validation_nonregression_pass"]]
    if accepted.empty:
        return search.reset_index(drop=True), default, "FALLBACK_DEFAULT_NO_VALIDATED_SHORTLIST"
    selected_id = int(accepted.iloc[0]["candidate_id"])
    return search.reset_index(drop=True), parameters_by_id[selected_id], "DISCOVERY_RANKED_VALIDATION_PASS"


def choose_earliest_validation_stage(
    stage_metrics: pd.DataFrame,
    *,
    selection_config: dict[str, Any],
) -> tuple[str, dict[str, bool]]:
    """Choose the earliest stage non-inferior to the prespecified T-1 rule."""
    validation = stage_metrics[stage_metrics["split"].eq("VALIDATION")]
    reference = validation[
        validation["variant"].eq("PRESPECIFIED")
        & validation["stage"].eq("T1_PRICE_VOLUME_CONFIRM")
    ].iloc[0]
    decisions: dict[str, bool] = {}
    for stage in STAGES:
        candidate = validation[
            validation["variant"].eq("OPTIMIZED") & validation["stage"].eq(stage)
        ].iloc[0]
        decisions[stage] = _noninferior(
            candidate.to_dict(),
            reference.to_dict(),
            selection_config,
            require_recall=True,
        )
    selected = next((stage for stage in STAGES if decisions[stage]), None)
    return selected or "T1_PRICE_VOLUME_CONFIRM", decisions


def build_monthly_metrics(
    rows: pd.DataFrame,
    *,
    selected_parameters: dict[str, EarlyStartParameters],
) -> pd.DataFrame:
    """Stress the frozen candidates separately in each holdout month."""
    holdout_months = sorted(
        rows.loc[rows["split"].eq("HOLDOUT"), "asof_date"]
        .dt.to_period("M")
        .astype(str)
        .unique()
    )
    records: list[dict[str, Any]] = []
    variants = {
        "PRESPECIFIED": {stage: default_parameters(stage) for stage in STAGES},
        "OPTIMIZED": selected_parameters,
    }
    for month in holdout_months:
        month_rows = rows[
            rows["asof_date"].dt.to_period("M").astype(str).eq(month)
        ].copy()
        month_rows["split"] = "MONTH"
        for variant, parameter_sets in variants.items():
            for stage, parameters in parameter_sets.items():
                metrics = classification_metrics(
                    month_rows,
                    parameter_mask(month_rows, parameters),
                    split="MONTH",
                )
                records.append(
                    {
                        "month": month,
                        "variant": variant,
                        "stage": stage,
                        "lead_trading_days": parameters.lead_trading_days,
                        **metrics,
                    }
                )
    return pd.DataFrame(records)


def run_optimizer(
    *,
    input_csv: Path,
    sqlite_path: Path,
    config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    analysis = config["analysis"]
    selection = config["selection"]
    labeled = pd.read_csv(input_csv, dtype={"stock_id": str})
    events = prepare_modeling_events(
        labeled,
        signal_start=analysis["signal_start"],
        signal_end=analysis["signal_end"],
        cooldown_trade_days=int(analysis["same_stock_cooldown_trade_days"]),
    )
    history = load_adjusted_history(
        sqlite_path,
        stock_ids=sorted(events["stock_id"].unique()),
        start_date=(events["asof_date"].min() - pd.Timedelta(days=500)).date().isoformat(),
        end_date=(events["asof_date"].max() - pd.Timedelta(days=1)).date().isoformat(),
    )
    snapshots = build_lead_snapshots(events, history)
    matrix = build_modeling_matrix(events, snapshots, split_config=analysis)
    searches: list[pd.DataFrame] = []
    selected_parameters: dict[str, EarlyStartParameters] = {}
    selection_reasons: dict[str, str] = {}
    for stage in STAGES:
        search, parameters, reason = search_stage(
            matrix,
            stage=stage,
            search_grid=config["search_grid"],
            selection_config=selection,
        )
        searches.append(search)
        selected_parameters[stage] = parameters
        selection_reasons[stage] = reason
    search_results = pd.concat(searches, ignore_index=True)

    metric_records: list[dict[str, Any]] = []
    for variant, parameter_sets in {
        "PRESPECIFIED": {stage: default_parameters(stage) for stage in STAGES},
        "OPTIMIZED": selected_parameters,
    }.items():
        for stage, parameters in parameter_sets.items():
            mask = parameter_mask(matrix, parameters)
            for split in ("DISCOVERY", "VALIDATION", "HOLDOUT"):
                metric_records.append(
                    {
                        "variant": variant,
                        "stage": stage,
                        "lead_trading_days": parameters.lead_trading_days,
                        **classification_metrics(matrix, mask, split=split),
                    }
                )
    stage_metrics = pd.DataFrame(metric_records)
    monthly_metrics = build_monthly_metrics(
        matrix,
        selected_parameters=selected_parameters,
    )
    validation_stage, validation_decisions = choose_earliest_validation_stage(
        stage_metrics,
        selection_config=selection,
    )
    holdout = stage_metrics[stage_metrics["split"].eq("HOLDOUT")]
    holdout_reference = holdout[
        holdout["variant"].eq("PRESPECIFIED")
        & holdout["stage"].eq("T1_PRICE_VOLUME_CONFIRM")
    ].iloc[0]
    holdout_stage_decisions: dict[str, bool] = {}
    for stage in STAGES:
        stage_row = holdout[
            holdout["variant"].eq("OPTIMIZED") & holdout["stage"].eq(stage)
        ].iloc[0]
        holdout_stage_decisions[stage] = _noninferior(
            stage_row.to_dict(),
            holdout_reference.to_dict(),
            selection,
            require_recall=True,
        ) and stage_row["selected_rows"] >= int(selection["minimum_holdout_rows"])
    holdout_pass = holdout_stage_decisions[validation_stage]
    earlier_verified = (
        validation_stage != "T1_PRICE_VOLUME_CONFIRM" and holdout_pass
    )
    final_stage = validation_stage if earlier_verified else "T1_PRICE_VOLUME_CONFIRM"
    summary = {
        "purpose": "earlier_start_detection_parameter_optimization",
        "market": "TW",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "signal_start": analysis["signal_start"],
        "signal_end": analysis["signal_end"],
        "target": f"D+5 adjusted close return >= {analysis['target_return_pct']}%",
        "event_rows_after_guards": int(len(matrix)),
        "split_rows": matrix["split"].value_counts().to_dict(),
        "purged_label_boundary_rows": int(
            matrix.attrs.get("purged_label_boundary_rows", 0)
        ),
        "search_candidates": int(len(search_results)),
        "selected_parameters": {
            stage: asdict(parameters) for stage, parameters in selected_parameters.items()
        },
        "selection_reasons": selection_reasons,
        "validation_earliest_candidate": validation_stage,
        "validation_noninferiority": validation_decisions,
        "holdout_selected_candidate_noninferiority_pass": bool(holdout_pass),
        "holdout_stage_noninferiority": holdout_stage_decisions,
        "earlier_detection_verified": bool(earlier_verified),
        "recommended_shadow_stage": final_stage,
        "recommended_lead_trading_days": LEAD_BY_STAGE[final_stage],
        "promotion_decision": "blocked_before_promotion_review",
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "four_component_report_role": (
            "primary_daily_strength_rank; early-start stage remains a separate watch-only tag"
        ),
    }
    result = {
        "matrix": matrix,
        "search_results": search_results,
        "stage_metrics": stage_metrics,
        "monthly_metrics": monthly_metrics,
        "selected_parameters": selected_parameters,
        "summary": summary,
    }
    write_outputs(result, output_dir=output_dir)
    return result


def write_outputs(result: dict[str, Any], *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result["matrix"].to_csv(
        output_dir / "zhu_walkline_early_start_modeling_rows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result["search_results"].to_csv(
        output_dir / "zhu_walkline_early_start_parameter_search.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result["stage_metrics"].to_csv(
        output_dir / "zhu_walkline_early_start_stage_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result["monthly_metrics"].to_csv(
        output_dir / "zhu_walkline_early_start_holdout_monthly_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    parameters = pd.DataFrame(
        [asdict(value) for value in result["selected_parameters"].values()]
    )
    parameters.to_csv(
        output_dir / "zhu_walkline_early_start_selected_parameters.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (output_dir / "zhu_walkline_early_start_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_early_start_summary.md").write_text(
        render_markdown(result),
        encoding="utf-8",
    )


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    metrics = result["stage_metrics"]
    lines = [
        "# 朱式走圖提早起漲影子參數最佳化",
        "",
        "## 結論",
        "",
        f"- 是否驗證可更早發現且維持準確度：`{summary['earlier_detection_verified']}`",
        f"- 建議影子階段：`{summary['recommended_shadow_stage']}`（提前 {summary['recommended_lead_trading_days']} 個交易日）",
        f"- 驗證期選出的最早候選：`{summary['validation_earliest_candidate']}`",
        f"- 驗證選定候選的未見樣本非劣性：`{summary['holdout_selected_candidate_noninferiority_pass']}`",
        "- 四項影子強度仍為日常報告主排序；本結果只增加 watch-only 提早觀察標籤。",
        "- `formal_champion_changed=False`；`formal_trade_effect=False`。",
        "",
        "## 無前視設計",
        "",
        f"- 訊號範圍：{summary['signal_start']} 至 {summary['signal_end']}。",
        "- discovery：2026-01～02；validation：2026-03～04；holdout：2026-05～06。",
        f"- discovery／validation 邊界剔除 D+5 標籤尚未成熟列：{summary['purged_label_boundary_rows']}。",
        f"- 排除公司行動、未成熟標籤並套同股 5 交易日 cooldown 後：{summary['event_rows_after_guards']} 筆。",
        f"- 搜尋 {summary['search_candidates']} 組有界參數；holdout 不參與調參。",
        "- 目標為 D+5 調整後收盤報酬 >=10%；並同看召回率、平衡準確率、虧損率與月份空窗。",
        "",
        "## 未見樣本（2026-05～06）",
        "",
        _metric_table(metrics[metrics["split"].eq("HOLDOUT")]),
        "",
        "## 未見樣本逐月壓力測試",
        "",
        _monthly_metric_table(result["monthly_metrics"]),
        "",
        "## 最佳化參數",
        "",
        "| 階段 | T-5量比上限 | 月線斜率正 | T-3漲幅下限 | T-3 K變化下限 | T-1漲幅下限 | T-1量比下限 | T-1站回月線 |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for stage in STAGES:
        params = result["selected_parameters"][stage]
        lines.append(
            "| {stage} | {v:.2f} | {slope} | {t3} | {k} | {t1} | {t1v} | {ma} |".format(
                stage=stage,
                v=params.t5_volume_ratio_max,
                slope=params.t5_require_positive_ma20_slope,
                t3=_format_optional(params.t3_daily_return_min_pct),
                k=_format_optional(params.t3_k_change_min),
                t1=_format_optional(params.t1_daily_return_min_pct),
                t1v=_format_optional(params.t1_volume_ratio_min),
                ma=params.t1_require_above_ma20,
            )
        )
    lines.extend(
        [
            "",
            "## 治理判定",
            "",
            "- `mode=shadow_observation_only`",
            "- `promotion_decision=blocked_before_promotion_review`",
            "- 多參數搜尋結果只允許影子觀察；需要更長期 walk-forward、成本與失敗歸因後才能另行審查。",
        ]
    )
    return "\n".join(lines) + "\n"


def default_parameters(stage: str) -> EarlyStartParameters:
    values: dict[str, Any] = {"stage": stage, "t5_volume_ratio_max": 0.75}
    if stage in {"T3_EARLY_TURN", "T1_PRICE_VOLUME_CONFIRM"}:
        values["t3_daily_return_min_pct"] = 0.0
    if stage == "T1_PRICE_VOLUME_CONFIRM":
        values.update(t1_daily_return_min_pct=0.0, t1_volume_ratio_min=0.70)
    return EarlyStartParameters(**values)


def _assign_splits(
    dates: pd.Series,
    label_dates: pd.Series,
    config: dict[str, Any],
) -> pd.Series:
    output = pd.Series("OUT_OF_SCOPE", index=dates.index, dtype="string")
    ranges = {
        "DISCOVERY": (config["discovery_start"], config["discovery_end"]),
        "VALIDATION": (config["validation_start"], config["validation_end"]),
        "HOLDOUT": (config["holdout_start"], config["holdout_end"]),
    }
    for split, (start, end) in ranges.items():
        signal_scope = dates.between(pd.Timestamp(start), pd.Timestamp(end))
        output.loc[signal_scope] = split
        if split in {"DISCOVERY", "VALIDATION"}:
            label_mature_by_boundary = label_dates.le(pd.Timestamp(end))
            output.loc[signal_scope & ~label_mature_by_boundary] = (
                "PURGED_LABEL_BOUNDARY"
            )
    return output


def _noninferior(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    config: dict[str, Any],
    *,
    require_recall: bool,
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
    if bool(config["require_all_months_nonempty"]):
        checks.append(candidate["empty_months"] == 0)
    if require_recall:
        checks.append(candidate["recall_gain_ge10"] >= reference["recall_gain_ge10"])
    return all(bool(value) for value in checks)


def _prefixed(values: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in values.items() if key != "split"}


def _divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _as_bool(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"1", "true", "yes"})


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _format_optional(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _metric_table(rows: pd.DataFrame) -> str:
    lines = [
        "| 類型 | 階段 | 筆數 | >=10%精確率 | >=10%召回率 | 平衡準確率 | >=20%率 | 虧損率 | D+5平均 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows.sort_values(["variant", "lead_trading_days"], ascending=[True, False]).itertuples():
        lines.append(
            f"| {row.variant} | {row.stage} | {row.selected_rows} | "
            f"{row.precision_gain_ge10:.2%} | {row.recall_gain_ge10:.2%} | "
            f"{row.balanced_accuracy_gain_ge10:.2%} | {row.gain_ge20_rate:.2%} | "
            f"{row.loss_rate:.2%} | {row.avg_d5_adjusted_return_pct:.2f}% |"
        )
    return "\n".join(lines)


def _monthly_metric_table(rows: pd.DataFrame) -> str:
    selected = rows[
        rows["variant"].eq("OPTIMIZED")
        | (
            rows["variant"].eq("PRESPECIFIED")
            & rows["stage"].eq("T1_PRICE_VOLUME_CONFIRM")
        )
    ]
    lines = [
        "| 月份 | 類型 | 階段 | 筆數 | >=10%精確率 | >=10%召回率 | 平衡準確率 | 虧損率 | D+5平均 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in selected.sort_values(
        ["month", "variant", "lead_trading_days"], ascending=[True, True, False]
    ).itertuples():
        lines.append(
            f"| {row.month} | {row.variant} | {row.stage} | {row.selected_rows} | "
            f"{row.precision_gain_ge10:.2%} | {row.recall_gain_ge10:.2%} | "
            f"{row.balanced_accuracy_gain_ge10:.2%} | {row.loss_rate:.2%} | "
            f"{row.avg_d5_adjusted_return_pct:.2f}% |"
        )
    return "\n".join(lines)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default=(
            "reports/zhu_walkline_kd_d5_groups_2026_01_06/"
            "zhu_walkline_kd_d5_labeled_rows.csv"
        ),
    )
    parser.add_argument("--config", default="config/zhu_walkline_early_start_optimizer.yaml")
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_early_start_optimizer_2026_01_06",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_yaml(_repo_path(args.config))
    zhu_config = _load_yaml(REPO_ROOT / "config/zhu_walkline_shadow.yaml")
    result = run_optimizer(
        input_csv=_repo_path(args.input_csv),
        sqlite_path=Path(zhu_config["data"]["sqlite_path"]),
        config=config,
        output_dir=_repo_path(args.output_dir),
    )
    summary = result["summary"]
    print(f"event_rows_after_guards={summary['event_rows_after_guards']}")
    print(f"search_candidates={summary['search_candidates']}")
    print(f"earlier_detection_verified={summary['earlier_detection_verified']}")
    print(f"recommended_shadow_stage={summary['recommended_shadow_stage']}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
