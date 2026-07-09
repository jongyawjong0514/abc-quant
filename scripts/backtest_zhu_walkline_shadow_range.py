"""Backtest Zhu walkline shadow observations across an as-of date range.

This script evaluates observation outcomes only. It does not create trade
orders, portfolio weights, holdings, or formal strategy state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any

import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

HORIZONS = (1, 3, 5, 10)
BASELINE_HORIZONS = (1, 3, 5)


def main(argv: list[str] | None = None) -> int:
    from abc_quant.data.local_tw_loader import load_future_price_rows, load_local_tw_bundle
    from abc_quant.features.market_rotation import load_concept_stock_map
    from abc_quant.signals.zhu_walkline_shadow import (
        build_zhu_walkline_shadow_result,
        compute_forward_evaluation,
    )

    args = _parse_args(argv)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])
    trading_dates = _load_trading_dates(sqlite_path, args.start_date, args.end_date)
    if not trading_dates:
        raise ValueError(f"No trading dates found from {args.start_date} to {args.end_date}")

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    concept_map = load_concept_stock_map(REPO_ROOT / "config" / "concept_stock_map.yaml")

    all_evaluations: list[pd.DataFrame] = []
    all_baselines: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []
    max_future_dates: list[str] = []
    start_time = time.perf_counter()
    for index, asof_date in enumerate(trading_dates, start=1):
        day_start = time.perf_counter()
        bundle = load_local_tw_bundle(config, asof=asof_date)
        result = build_zhu_walkline_shadow_result(
            bundle,
            concept_map=concept_map,
            web_records=[],
            top_n=args.top_n,
            web_research_used=False,
            config=config,
        )
        stock_ids = sorted(
            set(result.top_rise_candidates["stock_id"].astype(str))
            | set(result.top_fall_risks["stock_id"].astype(str))
        )
        future_prices = load_future_price_rows(
            sqlite_path,
            asof_date=result.asof_date,
            stock_ids=stock_ids,
            horizon_calendar_days=args.future_calendar_days,
        )
        if not future_prices.empty:
            max_future_dates.append(str(future_prices["date"].max().date()))
        evaluation_frame, _evaluation_summary = compute_forward_evaluation(result, future_prices)
        enriched = _enrich_evaluation(result, evaluation_frame)
        if not enriched.empty:
            all_evaluations.append(enriched)
        universe_future_prices = load_future_price_rows(
            sqlite_path,
            asof_date=result.asof_date,
            stock_ids=sorted(result.feature_matrix["stock_id"].astype(str).unique()),
            horizon_calendar_days=args.future_calendar_days,
        )
        if not universe_future_prices.empty:
            max_future_dates.append(str(universe_future_prices["date"].max().date()))
        universe_forward = _compute_universe_forward_returns(result, universe_future_prices)
        all_baselines.extend(
            _baseline_metrics_for_day(
                result,
                enriched,
                universe_forward,
                random_seed=args.random_seed,
            )
        )
        daily_row = _daily_metrics(result, enriched)
        daily_row["elapsed_seconds"] = round(time.perf_counter() - day_start, 3)
        daily_rows.append(daily_row)
        if args.verbose:
            print(
                f"[{index}/{len(trading_dates)}] {asof_date} "
                f"rise={daily_row['rise_count']} fall={daily_row['fall_count']} "
                f"eval={daily_row['evaluation_rows']} "
                f"d5_hit={daily_row.get('rise_hit_rate_d5', '')} "
                f"elapsed={daily_row['elapsed_seconds']}s",
                flush=True,
            )

    evaluations = pd.concat(all_evaluations, ignore_index=True) if all_evaluations else pd.DataFrame()
    baselines = pd.DataFrame(all_baselines)
    daily = pd.DataFrame(daily_rows)
    monthly = _monthly_metrics(evaluations)
    summary = _summary_payload(
        start_date=args.start_date,
        end_date=args.end_date,
        trading_dates=trading_dates,
        daily=daily,
        evaluations=evaluations,
        baselines=baselines,
        monthly=monthly,
        top_n=args.top_n,
        future_calendar_days=args.future_calendar_days,
        max_future_date_used=max(max_future_dates) if max_future_dates else None,
        elapsed_seconds=time.perf_counter() - start_time,
    )

    evaluation_path = output_dir / "zhu_walkline_range_evaluations.csv"
    daily_path = output_dir / "zhu_walkline_range_daily_metrics.csv"
    baseline_path = output_dir / "zhu_walkline_range_baseline_metrics.csv"
    monthly_path = output_dir / "zhu_walkline_range_monthly_metrics.csv"
    summary_json_path = output_dir / "zhu_walkline_range_summary.json"
    summary_md_path = output_dir / "zhu_walkline_range_summary.md"
    evaluations.to_csv(evaluation_path, index=False, encoding="utf-8-sig")
    daily.to_csv(daily_path, index=False, encoding="utf-8-sig")
    baselines.to_csv(baseline_path, index=False, encoding="utf-8-sig")
    monthly.to_csv(monthly_path, index=False, encoding="utf-8-sig")
    summary_json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    summary_md_path.write_text(_summary_markdown(summary, daily), encoding="utf-8")

    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"evaluation_csv={evaluation_path}")
    print(f"daily_metrics_csv={daily_path}")
    print(f"baseline_metrics_csv={baseline_path}")
    print(f"monthly_metrics_csv={monthly_path}")
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--top-n", type=int, default=30)
    parser.add_argument("--future-calendar-days", type=int, default=25)
    parser.add_argument("--random-seed", type=int, default=20260710)
    parser.add_argument("--output-dir", default="reports/zhu_walkline_shadow_backtest")
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


def _load_trading_dates(sqlite_path: Path, start_date: str, end_date: str) -> list[str]:
    query = """
        select distinct date
        from daily_ohlcv_features
        where date between ? and ?
        order by date
    """
    with sqlite3.connect(sqlite_path) as connection:
        rows = connection.execute(query, (start_date, end_date)).fetchall()
    return [str(row[0])[:10] for row in rows]


def _enrich_evaluation(result: Any, evaluation_frame: pd.DataFrame) -> pd.DataFrame:
    if evaluation_frame.empty:
        return evaluation_frame
    rise = result.top_bullish_watchlist.copy().reset_index(drop=True)
    rise["candidate_side"] = "rise"
    rise["rank"] = range(1, len(rise) + 1)
    fall = result.top_fall_risks.copy().reset_index(drop=True)
    fall["candidate_side"] = "fall"
    fall["rank"] = range(1, len(fall) + 1)
    metadata = pd.concat([rise, fall], ignore_index=True)
    keep_columns = [
        "asof_date",
        "stock_id",
        "candidate_side",
        "rank",
        "rise_score",
        "grade",
        "fall_risk_score",
        "risk_grade",
        "signal_stage",
        "trigger_type",
        "buy_observation_type",
        "buy_observation_detail_types",
        "buy_trigger_price",
        "buy_trigger_price_role",
        "sell_warning_type",
        "sell_warning_detail_types",
        "failure_type",
        "stop_reference",
        "market_state",
        "sector",
    ]
    for column in keep_columns:
        if column not in metadata.columns:
            metadata[column] = ""
    enriched = evaluation_frame.merge(
        metadata[keep_columns],
        on=["asof_date", "stock_id", "candidate_side"],
        how="left",
    )
    return enriched


def _daily_metrics(result: Any, evaluation_frame: pd.DataFrame) -> dict[str, Any]:
    row: dict[str, Any] = {
        "asof_date": result.asof_date,
        "mode": result.mode,
        "formal_champion_changed": result.formal_champion_changed,
        "formal_trade_effect": result.formal_trade_effect,
        "market_state": result.market.get("market_state", ""),
        "market_source": result.market.get("source", ""),
        "feature_count": len(result.feature_matrix),
        "rise_count": len(result.top_bullish_watchlist),
        "fall_count": len(result.top_fall_risks),
        "evaluation_rows": len(evaluation_frame),
    }
    for side in ("rise", "fall"):
        subset = evaluation_frame[evaluation_frame["candidate_side"] == side] if not evaluation_frame.empty else pd.DataFrame()
        row[f"{side}_empty"] = bool(subset.empty)
        for horizon in (1, 3, 5, 10):
            return_column = f"future_return_d{horizon}"
            hit_column = f"hit_d{horizon}"
            valid_rows, missing_rows = _valid_missing_counts(subset, return_column)
            row[f"{side}_valid_rows_d{horizon}"] = valid_rows
            row[f"{side}_missing_rows_d{horizon}"] = missing_rows
            row[f"{side}_hit_rate_d{horizon}"] = _mean_or_none(subset, hit_column)
            row[f"{side}_avg_forward_return_d{horizon}"] = _mean_or_none(subset, return_column)
            row[f"{side}_median_forward_return_d{horizon}"] = _median_or_none(subset, return_column)
        if side == "rise":
            row["rise_tail_loss_rate_d5"] = _threshold_rate(subset, "future_return_d5", threshold=-0.03, direction="<=")
        else:
            row["fall_tail_down_rate_d5"] = _threshold_rate(subset, "future_return_d5", threshold=-0.03, direction="<=")
            row["fall_adverse_rally_rate_d5"] = _threshold_rate(subset, "future_return_d5", threshold=0.03, direction=">=")
    return row


def _summary_payload(
    *,
    start_date: str,
    end_date: str,
    trading_dates: list[str],
    daily: pd.DataFrame,
    evaluations: pd.DataFrame,
    baselines: pd.DataFrame,
    monthly: pd.DataFrame,
    top_n: int,
    future_calendar_days: int,
    max_future_date_used: str | None,
    elapsed_seconds: float,
) -> dict[str, Any]:
    row_weighted_metrics = _side_metrics(evaluations, include_counts=True)
    baseline_metrics = _baseline_summary_metrics(baselines)
    excess_vs_baseline = _excess_vs_baseline(row_weighted_metrics, baseline_metrics)
    return {
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "resolved_start_date": trading_dates[0],
        "resolved_end_date": trading_dates[-1],
        "trading_day_count": len(trading_dates),
        "top_n": top_n,
        "future_calendar_days": future_calendar_days,
        "max_future_date_used": max_future_date_used,
        "market": "Taiwan stocks",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "no_formal_strategy_modified": True,
        "no_formal_champion_modified": True,
        "no_formal_trade_effect": True,
        "execution_assumption": "No executions; forward outcomes are observation-only, gross returns.",
        "cost_slippage_treatment": "Not applied because this backtest does not simulate trades or positions.",
        "no_lookahead": "Features are loaded with rows <= each asof_date; future rows are used only by evaluator outputs.",
        "daily_equal_weighted_metrics": _daily_equal_weighted_metrics(daily),
        "row_weighted_metrics": row_weighted_metrics,
        "valid_row_count_by_horizon": _valid_row_count_by_horizon(evaluations),
        "baseline_metrics": baseline_metrics,
        "excess_vs_baseline": excess_vs_baseline,
        "monthly_preview": _records(monthly),
        "monthly_rows": int(len(monthly)),
        "evaluation_rows": int(len(evaluations)),
        "baseline_rows": int(len(baselines)),
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "promotion_decision": "blocked_before_promotion_review",
    }


def _summary_markdown(summary: dict[str, Any], daily: pd.DataFrame) -> str:
    daily_means = summary["daily_equal_weighted_metrics"]
    row_weighted = summary["row_weighted_metrics"]
    lines = [
        "# Zhu Walkline Shadow Backtest",
        "",
        "本回測為 shadow observation only，不是投資建議，不是買賣指令。",
        "Daily equal-weighted 代表每天權重相同；row-weighted 代表每筆 evaluator row 權重相同。",
        "缺少未來資料的 horizon 會列為 missing，不會被當成 miss。",
        "",
        f"- 區間：{summary['resolved_start_date']} ~ {summary['resolved_end_date']}",
        f"- 交易日數：{summary['trading_day_count']}",
        f"- top_n：{summary['top_n']}",
        f"- evaluation_rows：{summary['evaluation_rows']}",
        f"- baseline_rows：{summary['baseline_rows']}",
        f"- max_future_date_used：{summary.get('max_future_date_used') or ''}",
        f"- mode={summary['mode']}",
        f"- formal_champion_changed={summary['formal_champion_changed']}",
        f"- formal_trade_effect={summary['formal_trade_effect']}",
        "- no formal strategy modified",
        "- no formal champion modified",
        "- no formal trade effect",
        "",
        "## Row-Weighted Observation Metrics",
        "",
        "| side | horizon | valid | missing | hit_rate | avg_return | median_return |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(_metrics_markdown_rows(row_weighted))
    lines.extend(
        [
            "",
            "## Daily Equal-Weighted Observation Metrics",
            "",
            "| side | horizon | hit_rate | avg_return | median_return |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    lines.extend(_daily_metrics_markdown_rows(daily_means))
    lines.extend(
        [
            "",
            "## Horizon Completeness",
            "",
            "| horizon | valid | missing |",
            "|---:|---:|---:|",
        ]
    )
    for horizon, payload in summary["valid_row_count_by_horizon"].items():
        lines.append(f"| {horizon} | {payload['valid_row_count']} | {payload['missing_row_count']} |")
    lines.extend(
        [
            "",
            "## Baseline Excess",
            "",
            "| side | baseline | horizon | excess_hit_rate | excess_avg_return |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for side, baseline_map in summary["excess_vs_baseline"].items():
        for baseline_type, horizon_map in baseline_map.items():
            for horizon, payload in horizon_map.items():
                lines.append(
                    f"| {side} | {baseline_type} | {horizon} | "
                    f"{_format_metric(payload.get('excess_hit_rate'))} | "
                    f"{_format_metric(payload.get('excess_avg_return'))} |"
                )
    lines.extend(
        [
            "",
            "## Monthly D5 Metrics",
            "",
            "| month | side | rows | valid_d5 | hit_d5 | avg_d5 | median_d5 | downside/adverse |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("monthly_preview", []):
        adverse = row.get("rise_tail_loss_rate_d5")
        if row.get("side") == "fall":
            adverse = row.get("fall_adverse_rally_rate_d5")
        lines.append(
            f"| {row.get('month')} | {row.get('side')} | {row.get('rows')} | "
            f"{row.get('valid_d5_rows')} | {_format_metric(row.get('hit_d5'))} | "
            f"{_format_metric(row.get('avg_d5'))} | {_format_metric(row.get('median_d5'))} | "
            f"{_format_metric(adverse)} |"
        )
    lines.extend(
        [
            "",
            "## Market State Counts",
            "",
            "| market_state | days |",
            "|---|---:|",
        ]
    )
    if "market_state" in daily.columns and not daily.empty:
        for state, count in daily["market_state"].value_counts(dropna=False).sort_index().items():
            lines.append(f"| {state} | {int(count)} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- 不產生交易指令",
            "- 不輸出絕對買賣建議",
            "- `promotion_decision=blocked_before_promotion_review`",
        ]
    )
    return "\n".join(lines) + "\n"


def _compute_universe_forward_returns(result: Any, future_prices: pd.DataFrame) -> pd.DataFrame:
    if result.feature_matrix.empty:
        return pd.DataFrame()
    metadata_columns = [
        "stock_id",
        "stock_name",
        "close",
        "rise_score",
        "fall_risk_score",
        "market_state",
        "sector",
    ]
    metadata = result.feature_matrix.copy()
    for column in metadata_columns:
        if column not in metadata.columns:
            metadata[column] = ""
    metadata = metadata[metadata_columns].drop_duplicates("stock_id").rename(columns={"close": "asof_close"})
    if future_prices.empty:
        for horizon in HORIZONS:
            metadata[f"future_return_d{horizon}"] = pd.NA
        return metadata

    future = future_prices.copy()
    future["date"] = pd.to_datetime(future["date"], errors="raise")
    future = future.sort_values(["stock_id", "date"])
    rows: list[dict[str, Any]] = []
    for _, stock in metadata.iterrows():
        stock_future = future[future["stock_id"].astype(str) == str(stock["stock_id"])].reset_index(drop=True)
        row = stock.to_dict()
        asof_close = _number_or_none(stock.get("asof_close"))
        for horizon in HORIZONS:
            value: float | None = None
            if asof_close and len(stock_future) >= horizon:
                value = float(stock_future.loc[horizon - 1, "close"] / asof_close - 1.0)
            row[f"future_return_d{horizon}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def _baseline_metrics_for_day(
    result: Any,
    evaluation_frame: pd.DataFrame,
    universe_forward: pd.DataFrame,
    *,
    random_seed: int,
) -> list[dict[str, Any]]:
    if universe_forward.empty:
        return []
    rows: list[dict[str, Any]] = []
    for side in ("rise", "fall"):
        candidate_count = (
            int((evaluation_frame["candidate_side"] == side).sum())
            if not evaluation_frame.empty and "candidate_side" in evaluation_frame.columns
            else 0
        )
        rows.append(
            _baseline_row(
                result=result,
                side=side,
                baseline_type="all_market",
                candidate_count=candidate_count,
                frame=universe_forward,
            )
        )
        if candidate_count > 0:
            sample_size = min(candidate_count, len(universe_forward))
            random_frame = universe_forward.sample(
                n=sample_size,
                random_state=_stable_seed(random_seed, result.asof_date, side, "random_same_count"),
            )
        else:
            random_frame = universe_forward.iloc[0:0]
        rows.append(
            _baseline_row(
                result=result,
                side=side,
                baseline_type="random_same_count",
                candidate_count=candidate_count,
                frame=random_frame,
            )
        )
        rows.extend(_score_decile_baseline_rows(result, side, candidate_count, universe_forward))
    return rows


def _baseline_row(
    *,
    result: Any,
    side: str,
    baseline_type: str,
    candidate_count: int,
    frame: pd.DataFrame,
    decile: int | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "asof_date": result.asof_date,
        "market_state": result.market.get("market_state", ""),
        "side": side,
        "baseline_type": baseline_type,
        "decile": decile if decile is not None else "",
        "candidate_count": candidate_count,
        "baseline_rows": int(len(frame)),
    }
    metrics = _metrics_for_return_frame(frame, side, horizons=BASELINE_HORIZONS)
    for horizon, payload in metrics.items():
        suffix = horizon.lower()
        row[f"valid_rows_{suffix}"] = payload["valid_row_count"]
        row[f"missing_rows_{suffix}"] = payload["missing_row_count"]
        row[f"hit_rate_{suffix}"] = payload["hit_rate"]
        row[f"avg_forward_return_{suffix}"] = payload["average_return"]
        row[f"median_forward_return_{suffix}"] = payload["median_return"]
    return row


def _score_decile_baseline_rows(
    result: Any,
    side: str,
    candidate_count: int,
    universe_forward: pd.DataFrame,
) -> list[dict[str, Any]]:
    score_column = "rise_score" if side == "rise" else "fall_risk_score"
    if score_column not in universe_forward.columns:
        return []
    scored = universe_forward.copy()
    scored["_score"] = pd.to_numeric(scored[score_column], errors="coerce")
    scored = scored[scored["_score"].notna()].copy()
    if scored.empty:
        return []
    if scored["_score"].nunique() >= 2:
        scored["_decile"] = pd.qcut(scored["_score"], q=10, labels=False, duplicates="drop")
        scored["_decile"] = pd.to_numeric(scored["_decile"], errors="coerce") + 1
    else:
        scored["_decile"] = 1
    rows: list[dict[str, Any]] = []
    for decile in sorted(pd.to_numeric(scored["_decile"], errors="coerce").dropna().astype(int).unique()):
        frame = scored[scored["_decile"] == decile].drop(columns=["_score", "_decile"])
        rows.append(
            _baseline_row(
                result=result,
                side=side,
                baseline_type=f"score_decile_{decile}",
                candidate_count=candidate_count,
                frame=frame,
                decile=int(decile),
            )
        )
    return rows


def _daily_equal_weighted_metrics(daily: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for side in ("rise", "fall"):
        result[side] = {}
        for horizon in HORIZONS:
            suffix = f"d{horizon}"
            result[side][f"D{horizon}"] = {
                "hit_rate": _mean_or_none(daily, f"{side}_hit_rate_{suffix}"),
                "average_return": _mean_or_none(daily, f"{side}_avg_forward_return_{suffix}"),
                "median_return": _mean_or_none(daily, f"{side}_median_forward_return_{suffix}"),
            }
        if side == "rise":
            result[side]["tail_loss_rate_d5"] = _mean_or_none(daily, "rise_tail_loss_rate_d5")
        else:
            result[side]["tail_down_rate_d5"] = _mean_or_none(daily, "fall_tail_down_rate_d5")
            result[side]["adverse_rally_rate_d5"] = _mean_or_none(daily, "fall_adverse_rally_rate_d5")
    return _clean_json(result)


def _side_metrics(evaluations: pd.DataFrame, *, include_counts: bool) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for side in ("rise", "fall"):
        subset = evaluations[evaluations["candidate_side"] == side] if "candidate_side" in evaluations.columns else pd.DataFrame()
        result[side] = _metrics_for_return_frame(subset, side, horizons=HORIZONS, include_counts=include_counts)
        if side == "rise":
            result[side]["tail_loss_rate_d5"] = _threshold_rate(
                subset,
                "future_return_d5",
                threshold=-0.03,
                direction="<=",
            )
        else:
            result[side]["tail_down_rate_d5"] = _threshold_rate(
                subset,
                "future_return_d5",
                threshold=-0.03,
                direction="<=",
            )
            result[side]["adverse_rally_rate_d5"] = _threshold_rate(
                subset,
                "future_return_d5",
                threshold=0.03,
                direction=">=",
            )
    return _clean_json(result)


def _metrics_for_return_frame(
    frame: pd.DataFrame,
    side: str,
    *,
    horizons: tuple[int, ...],
    include_counts: bool = True,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for horizon in horizons:
        return_column = f"future_return_d{horizon}"
        hit_column = f"hit_d{horizon}"
        returns = _numeric_series(frame, return_column)
        if hit_column in frame.columns:
            hits = _numeric_series(frame, hit_column)
        elif side == "rise":
            hits = (returns > 0).astype(float)
        else:
            hits = (returns < 0).astype(float)
        valid_rows, missing_rows = _valid_missing_counts(frame, return_column)
        payload: dict[str, Any] = {
            "hit_rate": None if hits.empty else float(hits.mean()),
            "average_return": None if returns.empty else float(returns.mean()),
            "median_return": None if returns.empty else float(returns.median()),
        }
        if include_counts:
            payload["valid_row_count"] = valid_rows
            payload["missing_row_count"] = missing_rows
        metrics[f"D{horizon}"] = payload
    return _clean_json(metrics)


def _baseline_summary_metrics(baselines: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if baselines.empty:
        return {"rise": {}, "fall": {}}
    for side in ("rise", "fall"):
        side_frame = baselines[baselines["side"] == side] if "side" in baselines.columns else pd.DataFrame()
        result[side] = {}
        if side_frame.empty or "baseline_type" not in side_frame.columns:
            continue
        for baseline_type, subset in side_frame.groupby("baseline_type", dropna=False):
            horizon_metrics: dict[str, Any] = {}
            for horizon in BASELINE_HORIZONS:
                suffix = f"d{horizon}"
                horizon_metrics[f"D{horizon}"] = {
                    "hit_rate": _mean_or_none(subset, f"hit_rate_{suffix}"),
                    "average_return": _mean_or_none(subset, f"avg_forward_return_{suffix}"),
                    "median_return": _mean_or_none(subset, f"median_forward_return_{suffix}"),
                    "valid_row_count": _sum_int(subset, f"valid_rows_{suffix}"),
                    "missing_row_count": _sum_int(subset, f"missing_rows_{suffix}"),
                }
            result[side][str(baseline_type)] = horizon_metrics
    return _clean_json(result)


def _excess_vs_baseline(row_weighted: dict[str, Any], baseline_metrics: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for side in ("rise", "fall"):
        result[side] = {}
        for baseline_type, horizon_map in baseline_metrics.get(side, {}).items():
            result[side][baseline_type] = {}
            for horizon in (f"D{value}" for value in BASELINE_HORIZONS):
                candidate = row_weighted.get(side, {}).get(horizon, {})
                baseline = horizon_map.get(horizon, {})
                result[side][baseline_type][horizon] = {
                    "excess_hit_rate": _subtract_optional(
                        candidate.get("hit_rate"),
                        baseline.get("hit_rate"),
                    ),
                    "excess_avg_return": _subtract_optional(
                        candidate.get("average_return"),
                        baseline.get("average_return"),
                    ),
                }
    return _clean_json(result)


def _valid_row_count_by_horizon(evaluations: pd.DataFrame) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for horizon in HORIZONS:
        valid_rows, missing_rows = _valid_missing_counts(evaluations, f"future_return_d{horizon}")
        result[f"D{horizon}"] = {
            "valid_row_count": valid_rows,
            "missing_row_count": missing_rows,
        }
    return result


def _monthly_metrics(evaluations: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "month",
        "side",
        "rows",
        "valid_d5_rows",
        "missing_d5_rows",
        "hit_d5",
        "avg_d5",
        "median_d5",
        "rise_tail_loss_rate_d5",
        "fall_tail_down_rate_d5",
        "fall_adverse_rally_rate_d5",
    ]
    if evaluations.empty or "asof_date" not in evaluations.columns:
        return pd.DataFrame(columns=columns)
    frame = evaluations.copy()
    frame["month"] = pd.to_datetime(frame["asof_date"], errors="coerce").dt.to_period("M").astype(str)
    rows: list[dict[str, Any]] = []
    for (month, side), subset in frame.groupby(["month", "candidate_side"], dropna=False):
        valid_rows, missing_rows = _valid_missing_counts(subset, "future_return_d5")
        row = {
            "month": str(month),
            "side": str(side),
            "rows": int(len(subset)),
            "valid_d5_rows": valid_rows,
            "missing_d5_rows": missing_rows,
            "hit_d5": _mean_or_none(subset, "hit_d5"),
            "avg_d5": _mean_or_none(subset, "future_return_d5"),
            "median_d5": _median_or_none(subset, "future_return_d5"),
            "rise_tail_loss_rate_d5": None,
            "fall_tail_down_rate_d5": None,
            "fall_adverse_rally_rate_d5": None,
        }
        if side == "rise":
            row["rise_tail_loss_rate_d5"] = _threshold_rate(
                subset,
                "future_return_d5",
                threshold=-0.03,
                direction="<=",
            )
        if side == "fall":
            row["fall_tail_down_rate_d5"] = _threshold_rate(
                subset,
                "future_return_d5",
                threshold=-0.03,
                direction="<=",
            )
            row["fall_adverse_rally_rate_d5"] = _threshold_rate(
                subset,
                "future_return_d5",
                threshold=0.03,
                direction=">=",
            )
        rows.append(row)
    return pd.DataFrame(rows, columns=columns).sort_values(["month", "side"]).reset_index(drop=True)


def _metrics_markdown_rows(metrics: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for side in ("rise", "fall"):
        for horizon in (f"D{value}" for value in HORIZONS):
            payload = metrics.get(side, {}).get(horizon, {})
            rows.append(
                f"| {side} | {horizon} | {payload.get('valid_row_count', 0)} | "
                f"{payload.get('missing_row_count', 0)} | {_format_metric(payload.get('hit_rate'))} | "
                f"{_format_metric(payload.get('average_return'))} | {_format_metric(payload.get('median_return'))} |"
            )
    return rows


def _daily_metrics_markdown_rows(metrics: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for side in ("rise", "fall"):
        for horizon in (f"D{value}" for value in HORIZONS):
            payload = metrics.get(side, {}).get(horizon, {})
            rows.append(
                f"| {side} | {horizon} | {_format_metric(payload.get('hit_rate'))} | "
                f"{_format_metric(payload.get('average_return'))} | {_format_metric(payload.get('median_return'))} |"
            )
    return rows


def _valid_missing_counts(frame: pd.DataFrame, column: str) -> tuple[int, int]:
    if frame.empty or column not in frame.columns:
        return 0, int(len(frame))
    values = pd.to_numeric(frame[column], errors="coerce")
    valid = int(values.notna().sum())
    return valid, int(len(frame) - valid)


def _threshold_rate(frame: pd.DataFrame, column: str, *, threshold: float, direction: str) -> float | None:
    values = _numeric_series(frame, column)
    if values.empty:
        return None
    if direction == "<=":
        return float((values <= threshold).mean())
    if direction == ">=":
        return float((values >= threshold).mean())
    raise ValueError(f"unsupported threshold direction: {direction}")


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def _number_or_none(value: Any) -> float | None:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return None
    return float(number)


def _mean_or_none(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_numeric(frame[column], errors="coerce").mean()
    return None if pd.isna(value) else float(value)


def _median_or_none(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_numeric(frame[column], errors="coerce").median()
    return None if pd.isna(value) else float(value)


def _tail_loss_rate(frame: pd.DataFrame) -> float | None:
    if frame.empty or "future_return_d5" not in frame.columns:
        return None
    returns = pd.to_numeric(frame["future_return_d5"], errors="coerce").dropna()
    if returns.empty:
        return None
    return float((returns <= -0.03).mean())


def _numeric_means(frame: pd.DataFrame) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for column in frame.columns:
        if column in {"asof_date", "mode", "market_state", "market_source"}:
            continue
        series = pd.to_numeric(frame[column], errors="coerce")
        if series.notna().any():
            result[column] = float(series.mean())
    return result


def _sum_int(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return int(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())


def _subtract_optional(left: Any, right: Any) -> float | None:
    left_number = _number_or_none(left)
    right_number = _number_or_none(right)
    if left_number is None or right_number is None:
        return None
    return float(left_number - right_number)


def _stable_seed(seed: int, *parts: Any) -> int:
    payload = "|".join([str(seed), *(str(part) for part in parts)])
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return _clean_json(frame.to_dict(orient="records"))


def _clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_json(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, pd.Period):
        return str(value)
    if value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "item"):
        return _clean_json(value.item())
    return value


def _format_metric(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.6f}"


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if value is pd.NA:
        return None
    if hasattr(value, "item"):
        return _json_default(value.item())
    if isinstance(value, float) and pd.isna(value):
        return None
    raise TypeError(f"Object is not JSON serializable: {type(value)!r}")


if __name__ == "__main__":
    raise SystemExit(main())
