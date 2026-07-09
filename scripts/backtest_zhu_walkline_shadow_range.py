"""Backtest Zhu walkline shadow observations across an as-of date range.

This script evaluates observation outcomes only. It does not create trade
orders, portfolio weights, holdings, or formal strategy state.
"""

from __future__ import annotations

import argparse
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
    daily_rows: list[dict[str, Any]] = []
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
        evaluation_frame, _evaluation_summary = compute_forward_evaluation(result, future_prices)
        enriched = _enrich_evaluation(result, evaluation_frame)
        if not enriched.empty:
            all_evaluations.append(enriched)
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
    daily = pd.DataFrame(daily_rows)
    summary = _summary_payload(
        start_date=args.start_date,
        end_date=args.end_date,
        trading_dates=trading_dates,
        daily=daily,
        evaluations=evaluations,
        top_n=args.top_n,
        future_calendar_days=args.future_calendar_days,
        elapsed_seconds=time.perf_counter() - start_time,
    )

    evaluation_path = output_dir / "zhu_walkline_range_evaluations.csv"
    daily_path = output_dir / "zhu_walkline_range_daily_metrics.csv"
    summary_json_path = output_dir / "zhu_walkline_range_summary.json"
    summary_md_path = output_dir / "zhu_walkline_range_summary.md"
    evaluations.to_csv(evaluation_path, index=False, encoding="utf-8-sig")
    daily.to_csv(daily_path, index=False, encoding="utf-8-sig")
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
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--top-n", type=int, default=30)
    parser.add_argument("--future-calendar-days", type=int, default=25)
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
            row[f"{side}_hit_rate_d{horizon}"] = _mean_or_none(subset, hit_column)
            row[f"{side}_avg_forward_return_d{horizon}"] = _mean_or_none(subset, return_column)
            row[f"{side}_median_forward_return_d{horizon}"] = _median_or_none(subset, return_column)
        row[f"{side}_tail_loss_rate_d5"] = _tail_loss_rate(subset)
    return row


def _summary_payload(
    *,
    start_date: str,
    end_date: str,
    trading_dates: list[str],
    daily: pd.DataFrame,
    evaluations: pd.DataFrame,
    top_n: int,
    future_calendar_days: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    return {
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "resolved_start_date": trading_dates[0],
        "resolved_end_date": trading_dates[-1],
        "trading_day_count": len(trading_dates),
        "top_n": top_n,
        "future_calendar_days": future_calendar_days,
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
        "daily_metric_means": _numeric_means(daily),
        "evaluation_rows": int(len(evaluations)),
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "promotion_decision": "blocked_before_promotion_review",
    }


def _summary_markdown(summary: dict[str, Any], daily: pd.DataFrame) -> str:
    means = summary["daily_metric_means"]
    lines = [
        "# Zhu Walkline Shadow Backtest",
        "",
        "本回測為 shadow observation only，不是投資建議，不是買賣指令。",
        "",
        f"- 區間：{summary['resolved_start_date']} ~ {summary['resolved_end_date']}",
        f"- 交易日數：{summary['trading_day_count']}",
        f"- top_n：{summary['top_n']}",
        f"- evaluation_rows：{summary['evaluation_rows']}",
        f"- mode={summary['mode']}",
        f"- formal_champion_changed={summary['formal_champion_changed']}",
        f"- formal_trade_effect={summary['formal_trade_effect']}",
        "- no formal strategy modified",
        "- no formal champion modified",
        "- no formal trade effect",
        "",
        "## Observation Outcome Means",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key in [
        "rise_hit_rate_d1",
        "rise_hit_rate_d3",
        "rise_hit_rate_d5",
        "rise_avg_forward_return_d5",
        "rise_median_forward_return_d5",
        "rise_tail_loss_rate_d5",
        "fall_hit_rate_d1",
        "fall_hit_rate_d3",
        "fall_hit_rate_d5",
        "fall_avg_forward_return_d5",
        "fall_median_forward_return_d5",
        "fall_tail_loss_rate_d5",
    ]:
        value = means.get(key)
        lines.append(f"| {key} | {_format_metric(value)} |")
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


def _format_metric(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.6f}"


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if pd.isna(value):
        return None
    raise TypeError(f"Object is not JSON serializable: {type(value)!r}")


if __name__ == "__main__":
    raise SystemExit(main())
