"""Run point-in-time sector diagnostics for the Zhu Walkline shadow research."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from abc_quant.validation.grouped_shadow_validation import (
    build_grouped_strategy_metrics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "zhu_walkline_grouped_validation.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "zhu_walkline_grouped_validation_2026_07_14"
MODE = "shadow_observation_only"


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("grouped validation config must be a mapping")
    return payload


def load_sector_membership(
    sqlite_path: Path,
    *,
    table: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Load one point-in-time sector row per stock/date from the trusted local mirror."""

    if table != "stock_pit_sector_membership_daily":
        raise ValueError("only the audited PIT sector table is allowed")
    query = f"""
        select
            date as observation_date,
            stock_id,
            stock_name,
            market,
            collection_name as sector,
            membership_mode,
            source_table as sector_source_table,
            source_detail as sector_source_detail,
            confidence as sector_confidence,
            effective_source_date,
            listing_date,
            pit_quality_rank
        from {table}
        where date between ? and ?
          and collection_layer = 'sector'
    """
    with sqlite3.connect(sqlite_path) as connection:
        frame = pd.read_sql_query(query, connection, params=[start_date, end_date])
    if frame.empty:
        raise ValueError("PIT sector membership query returned no rows")
    frame["observation_date"] = pd.to_datetime(
        frame["observation_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    if frame.duplicated(["observation_date", "stock_id"]).any():
        raise ValueError("PIT sector membership contains duplicate stock dates")
    source_dates = pd.to_datetime(frame["effective_source_date"], errors="coerce")
    observation_dates = pd.to_datetime(frame["observation_date"], errors="raise")
    if source_dates.gt(observation_dates).fillna(False).any():
        raise ValueError("PIT sector source date is later than observation date")
    return frame


def attach_sector_membership(
    modeling: pd.DataFrame, sector_membership: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join sector membership and return a split/mode coverage audit."""

    rows = modeling.copy()
    rows["observation_date"] = pd.to_datetime(
        rows["observation_date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    rows["stock_id"] = rows["stock_id"].astype(str).str.zfill(4)
    joined = rows.merge(
        sector_membership,
        on=["observation_date", "stock_id"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    audit = (
        joined.assign(
            membership_mode=joined["membership_mode"].fillna("UNMATCHED"),
            joined_sector=joined["_merge"].eq("both"),
        )
        .groupby(["split", "membership_mode"], dropna=False, as_index=False)
        .agg(
            rows=("stock_id", "size"),
            unique_stocks=("stock_id", "nunique"),
            trading_days=("asof_date", "nunique"),
            joined_rows=("joined_sector", "sum"),
        )
    )
    if not joined["_merge"].eq("both").all():
        missing = joined.loc[~joined["_merge"].eq("both"), ["observation_date", "stock_id"]]
        raise ValueError(f"sector PIT join is incomplete; missing rows={len(missing)}")
    joined = joined.drop(columns="_merge")
    return joined, audit


def build_strategy_summary(
    rows: pd.DataFrame,
    *,
    strategies: dict[str, str | None],
    tail_loss_threshold: float,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for strategy, column in strategies.items():
        selected = (
            pd.Series(True, index=rows.index)
            if column is None
            else rows[column].fillna(False).astype(bool)
        )
        chosen = rows.loc[selected]
        returns = pd.to_numeric(chosen["net_return_pct"], errors="raise")
        records.append(
            {
                "strategy": strategy,
                "selected_rows": int(len(chosen)),
                "selected_dates": int(chosen["asof_date"].nunique()),
                "selected_stocks": int(chosen["stock_id"].nunique()),
                "precision_gain_ge10": float(chosen["target_gain_ge10"].mean()),
                "mean_net_return_pct": float(returns.mean()),
                "median_net_return_pct": float(returns.median()),
                "loss_rate": float(returns.lt(0).mean()),
                "tail_loss_rate": float(returns.le(tail_loss_threshold).mean()),
            }
        )
    return pd.DataFrame(records)


def build_sector_comparisons(
    metrics: pd.DataFrame,
    *,
    baseline: str,
    challengers: list[str],
) -> pd.DataFrame:
    baseline_rows = metrics[metrics["strategy"].eq(baseline)].copy()
    records: list[pd.DataFrame] = []
    comparison_columns = [
        "sector",
        "selected_rows",
        "selected_gain_rate",
        "posterior_precision",
        "selected_mean_net_return_pct",
        "selected_loss_rate",
        "selected_tail_loss_rate",
    ]
    baseline_rows = baseline_rows[comparison_columns].rename(
        columns={column: f"baseline_{column}" for column in comparison_columns if column != "sector"}
    )
    for challenger in challengers:
        candidate = metrics[metrics["strategy"].eq(challenger)][comparison_columns]
        merged = candidate.merge(baseline_rows, on="sector", how="inner")
        merged.insert(0, "challenger", challenger)
        merged.insert(1, "baseline", baseline)
        merged["raw_precision_delta_pctpt"] = (
            merged["selected_gain_rate"] - merged["baseline_selected_gain_rate"]
        ) * 100.0
        merged["posterior_precision_delta_pctpt"] = (
            merged["posterior_precision"]
            - merged["baseline_posterior_precision"]
        ) * 100.0
        merged["mean_return_delta_pctpt"] = (
            merged["selected_mean_net_return_pct"]
            - merged["baseline_selected_mean_net_return_pct"]
        )
        merged["loss_rate_delta_pctpt"] = (
            merged["selected_loss_rate"] - merged["baseline_selected_loss_rate"]
        ) * 100.0
        merged["tail_loss_delta_pctpt"] = (
            merged["selected_tail_loss_rate"]
            - merged["baseline_selected_tail_loss_rate"]
        ) * 100.0
        records.append(merged)
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()


def build_date_concentration(
    rows: pd.DataFrame, *, strategies: dict[str, str | None]
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for strategy, column in strategies.items():
        selected = (
            pd.Series(True, index=rows.index)
            if column is None
            else rows[column].fillna(False).astype(bool)
        )
        daily = (
            rows.loc[selected]
            .groupby("asof_date", as_index=False)
            .size()
            .sort_values(["size", "asof_date"], ascending=[False, True])
        )
        total = int(daily["size"].sum())
        for rank, item in enumerate(daily.head(5).itertuples(index=False), start=1):
            records.append(
                {
                    "strategy": strategy,
                    "rank": rank,
                    "asof_date": str(item.asof_date),
                    "selected_rows": int(item.size),
                    "selected_share": int(item.size) / total if total else 0.0,
                }
            )
    return pd.DataFrame(records)


def build_top_date_exclusion_sensitivity(
    rows: pd.DataFrame,
    *,
    strategies: dict[str, str | None],
    threshold_strategy: str,
    top_dates: int,
    tail_loss_threshold: float,
) -> pd.DataFrame:
    column = strategies[threshold_strategy]
    if column is None:
        raise ValueError("threshold strategy must have a selection column")
    daily = (
        rows.loc[rows[column].fillna(False).astype(bool)]
        .groupby("asof_date")
        .size()
        .sort_values(ascending=False)
    )
    excluded = [str(value) for value in daily.head(top_dates).index]
    reduced = rows.loc[~rows["asof_date"].astype(str).isin(excluded)].copy()
    full = build_strategy_summary(
        rows,
        strategies=strategies,
        tail_loss_threshold=tail_loss_threshold,
    ).assign(sensitivity="FULL_HOLDOUT", excluded_dates="")
    without = build_strategy_summary(
        reduced,
        strategies=strategies,
        tail_loss_threshold=tail_loss_threshold,
    ).assign(
        sensitivity=f"EXCLUDE_{top_dates}_LARGEST_{threshold_strategy}_DATES",
        excluded_dates=",".join(excluded),
    )
    return pd.concat([full, without], ignore_index=True)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return value


def _format(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _markdown_table(frame: pd.DataFrame, columns: list[str], *, rows: int = 30) -> str:
    available = [column for column in columns if column in frame]
    if frame.empty or not available:
        return "_無可用資料_"
    shown = frame[available].head(rows)
    header = "| " + " | ".join(available) + " |"
    separator = "|" + "|".join(["---"] * len(available)) + "|"
    body = [
        "| "
        + " | ".join(_format(value).replace("|", "\\|") for value in row)
        + " |"
        for row in shown.itertuples(index=False, name=None)
    ]
    return "\n".join([header, separator, *body])


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    metrics = result["sector_metrics"]
    comparisons = result["sector_comparisons"]
    stable_minimum = int(summary["stable_group_rows"])
    threshold = metrics[
        metrics["strategy"].eq("TECH_BASE_THRESHOLD")
        & metrics["selected_rows"].ge(stable_minimum)
    ].sort_values("posterior_precision", ascending=False)
    t1 = metrics[
        metrics["strategy"].eq("PRESPECIFIED_T1")
        & metrics["selected_rows"].ge(stable_minimum)
    ].sort_values("posterior_precision", ascending=False)
    threshold_comparison = comparisons[
        comparisons["challenger"].eq("TECH_BASE_THRESHOLD")
        & comparisons["selected_rows"].ge(summary["minimum_report_rows"])
        & comparisons["baseline_selected_rows"].ge(summary["minimum_report_rows"])
    ].sort_values("posterior_precision_delta_pctpt", ascending=False)
    lines = [
        "# Zhu Walkline PIT 產業分層影子診斷",
        "",
        "## 結論",
        "",
        summary["plain_language_conclusion"],
        "",
        f"- 主要評估列：{summary['primary_rows']:,}；產業 {summary['primary_sector_count']} 個。",
        f"- PIT join 覆蓋率：{summary['pit_join_coverage']:.2%}。",
        f"- T-1 少於 20 筆的產業：{summary['t1_groups_below_20']} / {summary['t1_sector_count']}。",
        f"- 純技術高信心門檻少於 20 筆的產業：{summary['threshold_groups_below_20']} / {summary['threshold_sector_count']}。",
        "- 所有產業命中率均以 beta-binomial 經驗貝氏部分池化；小樣本會往整體平均收縮。",
        "- 這是診斷與影子排序，不是產業勝率排行榜，也不改正式策略。",
        "",
        "## 資料稽核",
        "",
        _markdown_table(
            result["join_audit"],
            ["split", "membership_mode", "rows", "unique_stocks", "trading_days", "joined_rows"],
        ),
        "",
        "主比較只使用 HOLDOUT 的 `point_in_time_observed_asof` 產業列；較早期 lifecycle proxy 不用來宣稱產業效果。",
        "",
        "## 全體策略摘要",
        "",
        _markdown_table(
            result["strategy_summary"],
            [
                "strategy",
                "selected_rows",
                "selected_dates",
                "precision_gain_ge10",
                "loss_rate",
                "tail_loss_rate",
                "mean_net_return_pct",
                "median_net_return_pct",
            ],
        ),
        "",
        "## 純技術高信心門檻：至少 50 筆的產業",
        "",
        _markdown_table(
            threshold,
            [
                "sector",
                "selected_rows",
                "selected_gain_rate",
                "posterior_precision",
                "posterior_precision_lower",
                "posterior_precision_upper",
                "precision_lift_vs_group_base",
                "selected_mean_net_return_pct",
                "selected_loss_rate",
                "selected_tail_loss_rate",
                "selected_share_of_strategy",
            ],
        ),
        "",
        "## 現行 T-1：至少 50 筆的產業",
        "",
        _markdown_table(
            t1,
            [
                "sector",
                "selected_rows",
                "selected_gain_rate",
                "posterior_precision",
                "posterior_precision_lower",
                "posterior_precision_upper",
                "precision_lift_vs_group_base",
                "selected_mean_net_return_pct",
                "selected_loss_rate",
                "selected_tail_loss_rate",
            ],
        ),
        "",
        "## 同產業比較：兩邊至少 20 筆",
        "",
        "下表仍是描述性診斷；多產業比較尚未做完整 FDR／雙向群聚檢定，不得依最大值調參。",
        "",
        _markdown_table(
            threshold_comparison,
            [
                "sector",
                "selected_rows",
                "baseline_selected_rows",
                "posterior_precision_delta_pctpt",
                "mean_return_delta_pctpt",
                "loss_rate_delta_pctpt",
                "tail_loss_delta_pctpt",
            ],
        ),
        "",
        "## 日期集中敏感度",
        "",
        _markdown_table(
            result["date_concentration"],
            ["strategy", "rank", "asof_date", "selected_rows", "selected_share"],
            rows=20,
        ),
        "",
        _markdown_table(
            result["top_date_sensitivity"],
            [
                "sensitivity",
                "excluded_dates",
                "strategy",
                "selected_rows",
                "precision_gain_ge10",
                "loss_rate",
                "tail_loss_rate",
                "mean_net_return_pct",
            ],
            rows=20,
        ),
        "",
        "## 概念股與股本",
        "",
        "- 概念股：`insufficient_data`。本機只有 2026-07-09／07-13 快照，不能回填 2026H1；改從 2026-07-09 起累積 forward shadow 多標籤歷史。",
        "- 股本：只可做 sensitivity。普通股股本檔可覆蓋大多數列，但下載版本不是不可變歷史 vintage；正式規模分組應優先使用當時自由流通市值，再輔以成交金額／週轉率。",
        "",
        "## 治理",
        "",
        f"- mode={MODE}",
        "- formal_champion_changed=False",
        "- formal_trade_effect=False",
        "- concept_status=insufficient_data_before_2026_07_09",
        "- share_capital_status=sensitivity_only_historical_vintage_unverified",
        "- next_required_gate=forward_shadow_after_2026_07_14",
        "",
    ]
    return "\n".join(lines)


def run(config: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    analysis = config["analysis"]
    data = config["data"]
    strategies = dict(config["strategies"])
    modeling_path = _repo_path(data["modeling_parquet"])
    modeling = pd.read_parquet(modeling_path)
    start_date = pd.to_datetime(modeling["observation_date"]).min().strftime("%Y-%m-%d")
    end_date = pd.to_datetime(modeling["observation_date"]).max().strftime("%Y-%m-%d")
    sector = load_sector_membership(
        Path(data["sqlite_path"]),
        table=data["sector_table"],
        start_date=start_date,
        end_date=end_date,
    )
    joined, join_audit = attach_sector_membership(modeling, sector)
    primary = joined[
        joined["split"].eq(analysis["split"])
        & joined["membership_mode"].eq(data["primary_membership_mode"])
        & ~joined["entry_locked_limit_up"].fillna(False).astype(bool)
    ].copy()
    if primary.empty:
        raise ValueError("grouped primary evaluation is empty")
    tail_threshold = float(analysis["tail_loss_net_return_pct"])
    sector_metrics, priors = build_grouped_strategy_metrics(
        primary,
        group_column="sector",
        strategies=strategies,
        tail_loss_threshold=tail_threshold,
        fallback_prior_strength=float(analysis["fallback_beta_prior_strength"]),
    )
    strategy_summary = build_strategy_summary(
        primary,
        strategies=strategies,
        tail_loss_threshold=tail_threshold,
    )
    challengers = [name for name in strategies if name != "PRESPECIFIED_T1"]
    sector_comparisons = build_sector_comparisons(
        sector_metrics,
        baseline="PRESPECIFIED_T1",
        challengers=challengers,
    )
    date_concentration = build_date_concentration(primary, strategies=strategies)
    sensitivity_strategies = {
        key: strategies[key]
        for key in ["PRESPECIFIED_T1", "TECH_BASE_THRESHOLD"]
    }
    top_date_sensitivity = build_top_date_exclusion_sensitivity(
        primary,
        strategies=sensitivity_strategies,
        threshold_strategy="TECH_BASE_THRESHOLD",
        top_dates=2,
        tail_loss_threshold=tail_threshold,
    )

    t1_groups = sector_metrics[
        sector_metrics["strategy"].eq("PRESPECIFIED_T1")
        & sector_metrics["selected_rows"].gt(0)
    ]
    threshold_groups = sector_metrics[
        sector_metrics["strategy"].eq("TECH_BASE_THRESHOLD")
        & sector_metrics["selected_rows"].gt(0)
    ]
    minimum_rows = int(analysis["minimum_report_rows"])
    comparable = sector_comparisons[
        sector_comparisons["challenger"].eq("TECH_BASE_THRESHOLD")
        & sector_comparisons["selected_rows"].ge(minimum_rows)
        & sector_comparisons["baseline_selected_rows"].ge(minimum_rows)
    ]
    threshold_breadth = {
        "comparable_sectors": int(len(comparable)),
        "posterior_precision_better_sectors": int(
            comparable["posterior_precision_delta_pctpt"].gt(0).sum()
        ),
        "mean_return_better_sectors": int(
            comparable["mean_return_delta_pctpt"].gt(0).sum()
        ),
        "loss_rate_better_sectors": int(
            comparable["loss_rate_delta_pctpt"].lt(0).sum()
        ),
        "tail_loss_better_sectors": int(
            comparable["tail_loss_delta_pctpt"].lt(0).sum()
        ),
    }
    plain = (
        "產業分層後仍不能直接宣布某產業勝率最高：多數群組樣本太少，原始勝率會誤導。"
        f"在兩邊都至少 {minimum_rows} 筆的 {threshold_breadth['comparable_sectors']} 個產業中，"
        f"純技術高信心門檻的收縮後命中較高者有 {threshold_breadth['posterior_precision_better_sectors']} 個，"
        f"平均淨報酬較高者有 {threshold_breadth['mean_return_better_sectors']} 個。"
        "這表示產業結構值得納入診斷，但還不足以為各產業設定不同參數；先做前向影子驗證。"
    )
    summary = {
        "purpose": "pit_sector_grouped_shadow_validation",
        "market": analysis["market"],
        "currency": analysis["currency"],
        "timezone": analysis["timezone"],
        "as_of": analysis["as_of"],
        "split": analysis["split"],
        "source_modeling_rows": str(modeling_path),
        "source_modeling_row_count": int(len(modeling)),
        "pit_join_coverage": float(joined["sector"].notna().mean()),
        "primary_rows": int(len(primary)),
        "primary_sector_count": int(primary["sector"].nunique()),
        "primary_membership_mode": data["primary_membership_mode"],
        "minimum_report_rows": minimum_rows,
        "stable_group_rows": int(analysis["stable_group_rows"]),
        "t1_sector_count": int(len(t1_groups)),
        "t1_groups_below_20": int(t1_groups["selected_rows"].lt(20).sum()),
        "threshold_sector_count": int(len(threshold_groups)),
        "threshold_groups_below_20": int(
            threshold_groups["selected_rows"].lt(20).sum()
        ),
        "threshold_breadth": threshold_breadth,
        "concept_status": config["governance"]["concept_status"],
        "share_capital_status": config["governance"]["share_capital_status"],
        "promotion_decision": config["governance"]["promotion_decision"],
        "next_required_gate": config["governance"]["next_required_gate"],
        "plain_language_conclusion": plain,
        "mode": MODE,
        "formal_champion_changed": False,
        "formal_trade_effect": False,
    }
    result = {
        "summary": summary,
        "join_audit": join_audit,
        "strategy_summary": strategy_summary,
        "sector_metrics": sector_metrics,
        "sector_priors": priors,
        "sector_comparisons": sector_comparisons,
        "date_concentration": date_concentration,
        "top_date_sensitivity": top_date_sensitivity,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = "zhu_walkline_grouped_validation"
    for key in [
        "join_audit",
        "strategy_summary",
        "sector_metrics",
        "sector_priors",
        "sector_comparisons",
        "date_concentration",
        "top_date_sensitivity",
    ]:
        result[key].replace([np.inf, -np.inf], np.nan).to_csv(
            output_dir / f"{prefix}_{key}.csv",
            index=False,
            encoding="utf-8-sig",
        )
    (output_dir / f"{prefix}_summary.json").write_text(
        json.dumps(
            _json_safe(summary),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{prefix}_report.md").write_text(
        render_report(result), encoding="utf-8"
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run(load_config(args.config), output_dir=args.output_dir)
    print(f"mode={MODE}")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"report={args.output_dir / 'zhu_walkline_grouped_validation_report.md'}")
    print(result["summary"]["plain_language_conclusion"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
