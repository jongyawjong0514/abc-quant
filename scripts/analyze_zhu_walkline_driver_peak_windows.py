"""Analyze post-signal peak windows for the Zhu walkline driver screen.

This is a shadow/evaluator-only sidecar.  It starts from the already-formed
driver-screen rows, then looks forward to study where the future high occurred
and what the price/volume path looked like one trading week before and after
that high.  The future peak information is never used to form the screen.
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


DEFAULT_SCREENED_CSV = (
    "reports/zhu_walkline_driver_screen_backtest_2026_01_06/"
    "zhu_walkline_driver_screen_rows.csv"
)
DEFAULT_OUTPUT_DIR = "reports/zhu_walkline_driver_peak_windows_2026_01_06"

PRICE_COLUMNS = [
    "date",
    "stock_id",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "previous_close",
    "open_to_close_pct",
    "close_location_in_bar",
    "day_volume_ratio_20",
]

OUTPUT_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "sector",
    "close",
    "driver_score",
    "forward_return_pct",
    "peak_date",
    "peak_high",
    "peak_close",
    "peak_volume",
    "trading_days_to_peak",
    "pre_week_date",
    "pre_week_close",
    "post_week_date",
    "post_week_close",
    "asof_to_peak_high_return_pct",
    "pre_week_to_peak_high_return_pct",
    "peak_high_to_post_week_close_pct",
    "post_week_max_drawdown_from_peak_high_pct",
    "post_week_close_from_asof_pct",
    "peak_day_close_location_in_bar",
    "peak_day_upper_shadow_pct",
    "peak_day_close_from_high_pct",
    "peak_volume_vs_pre_week_avg",
    "peak_timing_bucket",
    "peak_gain_bucket",
    "post_peak_fade_bucket",
    "peak_window_pattern",
]

STOCK_OUTPUT_COLUMNS = [
    "stock_id",
    "stock_name",
    "sector",
    "selected_signal_count",
    "first_asof_date",
    "last_asof_date",
    "source_asof_date",
    "source_close",
    "driver_score",
    "forward_return_pct",
    "peak_date",
    "peak_high",
    "peak_close",
    "peak_volume",
    "trading_days_to_peak",
    "pre_week_date",
    "pre_week_close",
    "post_week_date",
    "post_week_close",
    "source_asof_to_peak_high_return_pct",
    "pre_week_to_peak_high_return_pct",
    "peak_high_to_post_week_close_pct",
    "post_week_max_drawdown_from_peak_high_pct",
    "post_week_close_from_source_asof_pct",
    "peak_day_close_location_in_bar",
    "peak_day_upper_shadow_pct",
    "peak_day_close_from_high_pct",
    "peak_volume_vs_pre_week_avg",
    "peak_timing_bucket",
    "peak_gain_bucket",
    "post_peak_fade_bucket",
    "peak_window_pattern",
]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])
    screened_path = REPO_ROOT / args.screened_csv
    screened = pd.read_csv(screened_path, dtype={"stock_id": str})
    if screened.empty:
        raise ValueError(f"screened rows are empty: {screened_path}")

    prices = _load_price_rows(
        sqlite_path=sqlite_path,
        selected=screened,
        peak_horizon_trading_days=args.peak_horizon_trading_days,
        context_trading_days=args.context_trading_days,
    )
    peak_rows = build_peak_window_rows(
        screened,
        prices=prices,
        peak_horizon_trading_days=args.peak_horizon_trading_days,
        context_trading_days=args.context_trading_days,
    )
    stock_peak_rows = build_stock_peak_rows(peak_rows)
    summary = build_summary_payload(
        peak_rows,
        stock_peak_rows=stock_peak_rows,
        screened_csv=args.screened_csv,
        peak_horizon_trading_days=args.peak_horizon_trading_days,
        context_trading_days=args.context_trading_days,
    )

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_outputs(peak_rows, stock_peak_rows, summary, output_dir=output_dir)

    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"peak_windows_csv={output_dir / 'zhu_walkline_driver_peak_windows.csv'}")
    print(f"stock_peak_windows_csv={output_dir / 'zhu_walkline_driver_stock_peak_windows.csv'}")
    print(f"summary_json={output_dir / 'zhu_walkline_driver_peak_windows_summary.json'}")
    print(f"summary_md={output_dir / 'zhu_walkline_driver_peak_windows_summary.md'}")
    return 0


def build_peak_window_rows(
    selected: pd.DataFrame,
    *,
    prices: pd.DataFrame,
    peak_horizon_trading_days: int,
    context_trading_days: int,
) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    selected_rows = selected.copy()
    selected_rows["stock_id"] = selected_rows["stock_id"].astype(str).str.zfill(4)
    selected_rows["asof_date"] = pd.to_datetime(selected_rows["asof_date"]).dt.strftime("%Y-%m-%d")
    price_rows = prices.copy()
    price_rows["stock_id"] = price_rows["stock_id"].astype(str).str.zfill(4)
    price_rows["date"] = pd.to_datetime(price_rows["date"]).dt.strftime("%Y-%m-%d")
    price_rows = price_rows.sort_values(["stock_id", "date"]).reset_index(drop=True)

    records: list[dict[str, Any]] = []
    grouped_prices = {stock_id: group.reset_index(drop=True) for stock_id, group in price_rows.groupby("stock_id")}
    for _, row in selected_rows.iterrows():
        stock_id = str(row["stock_id"]).zfill(4)
        history = grouped_prices.get(stock_id)
        if history is None or history.empty:
            records.append(_missing_record(row, "NO_PRICE_HISTORY"))
            continue
        matches = history.index[history["date"].eq(str(row["asof_date"]))]
        if len(matches) == 0:
            records.append(_missing_record(row, "NO_ASOF_PRICE"))
            continue
        asof_index = int(matches[0])
        start = asof_index + 1
        stop = min(len(history), asof_index + peak_horizon_trading_days + 1)
        future = history.iloc[start:stop].copy()
        if future.empty:
            records.append(_missing_record(row, "NO_FUTURE_WINDOW"))
            continue
        future["high"] = pd.to_numeric(future["high"], errors="coerce")
        future = future.dropna(subset=["high"])
        if future.empty:
            records.append(_missing_record(row, "NO_FUTURE_HIGH"))
            continue
        peak_index = int(future["high"].idxmax())
        record = _peak_record(
            row,
            history=history,
            asof_index=asof_index,
            peak_index=peak_index,
            context_trading_days=context_trading_days,
            peak_horizon_trading_days=peak_horizon_trading_days,
        )
        records.append(record)
    return _clean_frame(pd.DataFrame(records, columns=OUTPUT_COLUMNS))


def build_stock_peak_rows(peak_rows: pd.DataFrame) -> pd.DataFrame:
    if peak_rows.empty:
        return pd.DataFrame(columns=STOCK_OUTPUT_COLUMNS)
    rows = peak_rows.copy()
    rows["stock_id"] = rows["stock_id"].astype(str).str.zfill(4)
    rows["peak_high"] = pd.to_numeric(rows["peak_high"], errors="coerce")
    valid = rows[rows["peak_high"].notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=STOCK_OUTPUT_COLUMNS)
    signal_counts = (
        valid.groupby("stock_id", as_index=False)
        .agg(
            selected_signal_count=("asof_date", "size"),
            first_asof_date=("asof_date", "min"),
            last_asof_date=("asof_date", "max"),
        )
    )
    winners = (
        valid.sort_values(["stock_id", "peak_high", "peak_date", "asof_date"], ascending=[True, False, True, True])
        .groupby("stock_id", as_index=False)
        .head(1)
        .copy()
    )
    winners = winners.merge(signal_counts, on="stock_id", how="left")
    winners = winners.rename(
        columns={
            "asof_date": "source_asof_date",
            "close": "source_close",
            "asof_to_peak_high_return_pct": "source_asof_to_peak_high_return_pct",
            "post_week_close_from_asof_pct": "post_week_close_from_source_asof_pct",
        }
    )
    for column in STOCK_OUTPUT_COLUMNS:
        if column not in winners.columns:
            winners[column] = ""
    return _clean_frame(winners[STOCK_OUTPUT_COLUMNS].sort_values(["peak_high", "stock_id"], ascending=[False, True]))


def build_summary_payload(
    peak_rows: pd.DataFrame,
    *,
    stock_peak_rows: pd.DataFrame,
    screened_csv: str,
    peak_horizon_trading_days: int,
    context_trading_days: int,
) -> dict[str, Any]:
    rows = peak_rows.copy()
    valid = rows[pd.to_numeric(rows.get("peak_high"), errors="coerce").notna()].copy()
    stock_valid = stock_peak_rows[pd.to_numeric(stock_peak_rows.get("peak_high"), errors="coerce").notna()].copy()
    summary = {
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "purpose": "driver_screen_post_signal_peak_window_analysis",
        "screened_csv": screened_csv,
        "peak_horizon_trading_days": int(peak_horizon_trading_days),
        "context_trading_days": int(context_trading_days),
        "future_peak_is_evaluator_only": True,
        "no_formal_strategy_modified": True,
        "no_formal_champion_modified": True,
        "no_formal_trade_effect": True,
        "row_count": int(len(rows)),
        "valid_peak_rows": int(len(valid)),
        "unique_stocks": int(valid["stock_id"].nunique()) if not valid.empty else 0,
        "asof_date_count": int(valid["asof_date"].nunique()) if not valid.empty else 0,
        "overall_metrics": _overall_metrics(valid),
        "stock_level_row_count": int(len(stock_valid)),
        "stock_level_metrics": _stock_level_metrics(stock_valid),
        "peak_timing_bucket": _bucket_summary(valid, "peak_timing_bucket"),
        "peak_gain_bucket": _bucket_summary(valid, "peak_gain_bucket"),
        "post_peak_fade_bucket": _bucket_summary(valid, "post_peak_fade_bucket"),
        "peak_window_pattern": _bucket_summary(valid, "peak_window_pattern"),
        "sector_summary": _group_summary(valid, "sector", min_rows=20),
        "stock_peak_window_pattern": _stock_bucket_summary(stock_valid, "peak_window_pattern"),
        "stock_sector_summary": _stock_group_summary(stock_valid, "sector", min_rows=5),
        "driver_reason_note": "driver reasons remain as-of features; peak fields are forward labels for review only",
        "promotion_decision": "blocked_before_promotion_review",
    }
    return _json_clean(summary)


def _peak_record(
    selected_row: pd.Series,
    *,
    history: pd.DataFrame,
    asof_index: int,
    peak_index: int,
    context_trading_days: int,
    peak_horizon_trading_days: int,
) -> dict[str, Any]:
    peak = history.iloc[peak_index]
    pre_index = max(0, peak_index - context_trading_days)
    post_index = min(len(history) - 1, peak_index + context_trading_days)
    pre = history.iloc[pre_index]
    post = history.iloc[post_index]
    post_window = history.iloc[peak_index : post_index + 1].copy()
    pre_window = history.iloc[pre_index:peak_index].copy()

    asof_close = _float(selected_row.get("close"))
    peak_high = _float(peak.get("high"))
    peak_close = _float(peak.get("close"))
    pre_close = _float(pre.get("close"))
    post_close = _float(post.get("close"))
    post_low = pd.to_numeric(post_window.get("low"), errors="coerce").min()
    peak_volume = _float(peak.get("volume"))
    pre_avg_volume = pd.to_numeric(pre_window.get("volume"), errors="coerce").mean() if not pre_window.empty else None
    upper_shadow_pct = _upper_shadow_pct(peak)
    close_from_high_pct = _pct(peak_close, peak_high)
    peak_day_location = _float(peak.get("close_location_in_bar"))
    trading_days_to_peak = int(peak_index - asof_index)
    post_fade = _pct(post_close, peak_high)
    post_drawdown = _pct(post_low, peak_high)
    asof_to_peak = _pct(peak_high, asof_close)

    return {
        "asof_date": selected_row.get("asof_date"),
        "stock_id": str(selected_row.get("stock_id")).zfill(4),
        "stock_name": selected_row.get("stock_name", ""),
        "sector": selected_row.get("sector", ""),
        "close": asof_close,
        "driver_score": _float(selected_row.get("driver_score")),
        "forward_return_pct": _float(selected_row.get("forward_return_pct")),
        "peak_date": peak.get("date"),
        "peak_high": peak_high,
        "peak_close": peak_close,
        "peak_volume": peak_volume,
        "trading_days_to_peak": trading_days_to_peak,
        "pre_week_date": pre.get("date"),
        "pre_week_close": pre_close,
        "post_week_date": post.get("date"),
        "post_week_close": post_close,
        "asof_to_peak_high_return_pct": asof_to_peak,
        "pre_week_to_peak_high_return_pct": _pct(peak_high, pre_close),
        "peak_high_to_post_week_close_pct": post_fade,
        "post_week_max_drawdown_from_peak_high_pct": post_drawdown,
        "post_week_close_from_asof_pct": _pct(post_close, asof_close),
        "peak_day_close_location_in_bar": peak_day_location,
        "peak_day_upper_shadow_pct": upper_shadow_pct,
        "peak_day_close_from_high_pct": close_from_high_pct,
        "peak_volume_vs_pre_week_avg": _ratio(peak_volume, pre_avg_volume),
        "peak_timing_bucket": _peak_timing_bucket(trading_days_to_peak),
        "peak_gain_bucket": _peak_gain_bucket(asof_to_peak),
        "post_peak_fade_bucket": _post_peak_fade_bucket(post_fade),
        "peak_window_pattern": _peak_window_pattern(
            trading_days_to_peak=trading_days_to_peak,
            peak_day_close_location_in_bar=peak_day_location,
            peak_day_upper_shadow_pct=upper_shadow_pct,
            post_peak_fade_pct=post_fade,
            peak_horizon_trading_days=peak_horizon_trading_days,
        ),
    }


def _missing_record(selected_row: pd.Series, reason: str) -> dict[str, Any]:
    record = {column: "" for column in OUTPUT_COLUMNS}
    for column in ["asof_date", "stock_id", "stock_name", "sector", "close", "driver_score", "forward_return_pct"]:
        record[column] = selected_row.get(column, "")
    record["stock_id"] = str(record["stock_id"]).zfill(4) if record["stock_id"] != "" else ""
    record["peak_window_pattern"] = reason
    return record


def _load_price_rows(
    *,
    sqlite_path: Path,
    selected: pd.DataFrame,
    peak_horizon_trading_days: int,
    context_trading_days: int,
) -> pd.DataFrame:
    stock_ids = sorted({str(value).zfill(4) for value in selected["stock_id"].dropna().unique()})
    start_date = str(pd.to_datetime(selected["asof_date"]).min().date())
    max_asof = str(pd.to_datetime(selected["asof_date"]).max().date())
    calendar_padding_days = int((peak_horizon_trading_days + context_trading_days + 10) * 2)
    end_date = str((pd.to_datetime(max_asof) + pd.Timedelta(days=calendar_padding_days)).date())
    if not stock_ids:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select {", ".join(PRICE_COLUMNS)}
        from daily_ohlcv_features
        where date between ? and ?
          and stock_id in ({placeholders})
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query, connection, params=[start_date, end_date, *stock_ids])


def _overall_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    metrics = {
        "avg_trading_days_to_peak": _series_mean(frame, "trading_days_to_peak"),
        "median_trading_days_to_peak": _series_median(frame, "trading_days_to_peak"),
        "avg_asof_to_peak_high_return_pct": _series_mean(frame, "asof_to_peak_high_return_pct"),
        "median_asof_to_peak_high_return_pct": _series_median(frame, "asof_to_peak_high_return_pct"),
        "avg_peak_high_to_post_week_close_pct": _series_mean(frame, "peak_high_to_post_week_close_pct"),
        "median_peak_high_to_post_week_close_pct": _series_median(frame, "peak_high_to_post_week_close_pct"),
        "avg_post_week_max_drawdown_from_peak_high_pct": _series_mean(frame, "post_week_max_drawdown_from_peak_high_pct"),
        "median_post_week_max_drawdown_from_peak_high_pct": _series_median(frame, "post_week_max_drawdown_from_peak_high_pct"),
        "early_peak_1_5d_rate": _rate(frame["peak_timing_bucket"].eq("D01_05")),
        "peak_gain_ge_20pct_rate": _rate(pd.to_numeric(frame["asof_to_peak_high_return_pct"], errors="coerce") >= 20.0),
        "post_fade_le_neg10pct_rate": _rate(pd.to_numeric(frame["peak_high_to_post_week_close_pct"], errors="coerce") <= -10.0),
        "post_drawdown_le_neg15pct_rate": _rate(
            pd.to_numeric(frame["post_week_max_drawdown_from_peak_high_pct"], errors="coerce") <= -15.0
        ),
        "avg_peak_volume_vs_pre_week_avg": _series_mean(frame, "peak_volume_vs_pre_week_avg"),
        "median_peak_volume_vs_pre_week_avg": _series_median(frame, "peak_volume_vs_pre_week_avg"),
    }
    return _round_dict(metrics)


def _bucket_summary(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if frame.empty or column not in frame.columns:
        return []
    total = len(frame)
    records = []
    for value, group in frame.groupby(column, dropna=False):
        records.append(
            {
                column: "" if pd.isna(value) else str(value),
                "rows": int(len(group)),
                "row_share": round(float(len(group) / total), 6),
                "unique_stocks": int(group["stock_id"].nunique()),
                "avg_asof_to_peak_high_return_pct": _round(_series_mean(group, "asof_to_peak_high_return_pct")),
                "median_asof_to_peak_high_return_pct": _round(_series_median(group, "asof_to_peak_high_return_pct")),
                "avg_peak_high_to_post_week_close_pct": _round(_series_mean(group, "peak_high_to_post_week_close_pct")),
                "avg_forward_return_pct": _round(_series_mean(group, "forward_return_pct")),
            }
        )
    return sorted(records, key=lambda item: (-item["rows"], item[column]))


def _group_summary(frame: pd.DataFrame, column: str, *, min_rows: int) -> list[dict[str, Any]]:
    if frame.empty or column not in frame.columns:
        return []
    records = []
    for value, group in frame.groupby(column, dropna=False):
        if len(group) < min_rows:
            continue
        records.append(
            {
                column: "" if pd.isna(value) else str(value),
                "rows": int(len(group)),
                "unique_stocks": int(group["stock_id"].nunique()),
                "avg_asof_to_peak_high_return_pct": _round(_series_mean(group, "asof_to_peak_high_return_pct")),
                "avg_peak_high_to_post_week_close_pct": _round(_series_mean(group, "peak_high_to_post_week_close_pct")),
                "post_fade_le_neg10pct_rate": _round(
                    _rate(pd.to_numeric(group["peak_high_to_post_week_close_pct"], errors="coerce") <= -10.0)
                ),
                "avg_forward_return_pct": _round(_series_mean(group, "forward_return_pct")),
            }
        )
    return sorted(records, key=lambda item: (-item["avg_asof_to_peak_high_return_pct"], -item["rows"]))


def _stock_level_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    metrics = {
        "avg_trading_days_to_peak": _series_mean(frame, "trading_days_to_peak"),
        "median_trading_days_to_peak": _series_median(frame, "trading_days_to_peak"),
        "avg_source_asof_to_peak_high_return_pct": _series_mean(frame, "source_asof_to_peak_high_return_pct"),
        "median_source_asof_to_peak_high_return_pct": _series_median(frame, "source_asof_to_peak_high_return_pct"),
        "avg_peak_high_to_post_week_close_pct": _series_mean(frame, "peak_high_to_post_week_close_pct"),
        "median_peak_high_to_post_week_close_pct": _series_median(frame, "peak_high_to_post_week_close_pct"),
        "early_peak_1_5d_rate": _rate(frame["peak_timing_bucket"].eq("D01_05")),
        "peak_gain_ge_20pct_rate": _rate(pd.to_numeric(frame["source_asof_to_peak_high_return_pct"], errors="coerce") >= 20.0),
        "post_fade_le_neg10pct_rate": _rate(pd.to_numeric(frame["peak_high_to_post_week_close_pct"], errors="coerce") <= -10.0),
    }
    return _round_dict(metrics)


def _stock_bucket_summary(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if frame.empty or column not in frame.columns:
        return []
    total = len(frame)
    records = []
    for value, group in frame.groupby(column, dropna=False):
        records.append(
            {
                column: "" if pd.isna(value) else str(value),
                "rows": int(len(group)),
                "row_share": round(float(len(group) / total), 6),
                "avg_source_asof_to_peak_high_return_pct": _round(
                    _series_mean(group, "source_asof_to_peak_high_return_pct")
                ),
                "avg_peak_high_to_post_week_close_pct": _round(_series_mean(group, "peak_high_to_post_week_close_pct")),
            }
        )
    return sorted(records, key=lambda item: (-item["rows"], item[column]))


def _stock_group_summary(frame: pd.DataFrame, column: str, *, min_rows: int) -> list[dict[str, Any]]:
    if frame.empty or column not in frame.columns:
        return []
    records = []
    for value, group in frame.groupby(column, dropna=False):
        if len(group) < min_rows:
            continue
        records.append(
            {
                column: "" if pd.isna(value) else str(value),
                "rows": int(len(group)),
                "avg_source_asof_to_peak_high_return_pct": _round(
                    _series_mean(group, "source_asof_to_peak_high_return_pct")
                ),
                "avg_peak_high_to_post_week_close_pct": _round(_series_mean(group, "peak_high_to_post_week_close_pct")),
            }
        )
    return sorted(records, key=lambda item: (-item["avg_source_asof_to_peak_high_return_pct"], -item["rows"]))


def _write_outputs(frame: pd.DataFrame, stock_frame: pd.DataFrame, summary: dict[str, Any], *, output_dir: Path) -> None:
    _clean_frame(frame).to_csv(
        output_dir / "zhu_walkline_driver_peak_windows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _clean_frame(stock_frame).to_csv(
        output_dir / "zhu_walkline_driver_stock_peak_windows.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (output_dir / "zhu_walkline_driver_peak_windows_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_driver_peak_windows_summary.md").write_text(
        _summary_markdown(summary),
        encoding="utf-8",
    )


def _summary_markdown(summary: dict[str, Any]) -> str:
    metrics = summary.get("overall_metrics", {})
    stock_metrics = summary.get("stock_level_metrics", {})
    lines = [
        "# Zhu Walkline Driver Screen Peak Window Analysis",
        "",
        "本輸出是 shadow observation / evaluator-only 研究 sidecar，不是買進名單，不是交易指令。",
        "最高價日期、前後一週價格變化都是事後標籤，只用來研究篩選後的走勢特徵。",
        "",
        "## Boundary",
        "",
        "- mode=shadow_observation_only",
        "- formal_champion_changed=False",
        "- formal_trade_effect=False",
        "- no formal strategy modified",
        "- no formal champion modified",
        "- no formal trade effect",
        "",
        "## Overall",
        "",
        f"- rows: {summary.get('row_count', 0)}",
        f"- valid_peak_rows: {summary.get('valid_peak_rows', 0)}",
        f"- unique_stocks: {summary.get('unique_stocks', 0)}",
        f"- avg_trading_days_to_peak: {_fmt(metrics.get('avg_trading_days_to_peak'))}",
        f"- median_trading_days_to_peak: {_fmt(metrics.get('median_trading_days_to_peak'))}",
        f"- avg_asof_to_peak_high_return_pct: {_fmt(metrics.get('avg_asof_to_peak_high_return_pct'))}",
        f"- median_asof_to_peak_high_return_pct: {_fmt(metrics.get('median_asof_to_peak_high_return_pct'))}",
        f"- avg_peak_high_to_post_week_close_pct: {_fmt(metrics.get('avg_peak_high_to_post_week_close_pct'))}",
        f"- median_peak_high_to_post_week_close_pct: {_fmt(metrics.get('median_peak_high_to_post_week_close_pct'))}",
        f"- early_peak_1_5d_rate: {_fmt(metrics.get('early_peak_1_5d_rate'))}",
        f"- peak_gain_ge_20pct_rate: {_fmt(metrics.get('peak_gain_ge_20pct_rate'))}",
        f"- post_fade_le_neg10pct_rate: {_fmt(metrics.get('post_fade_le_neg10pct_rate'))}",
        "",
        "## Stock Level",
        "",
        f"- stock_level_row_count: {summary.get('stock_level_row_count', 0)}",
        f"- avg_trading_days_to_peak: {_fmt(stock_metrics.get('avg_trading_days_to_peak'))}",
        f"- median_trading_days_to_peak: {_fmt(stock_metrics.get('median_trading_days_to_peak'))}",
        f"- avg_source_asof_to_peak_high_return_pct: {_fmt(stock_metrics.get('avg_source_asof_to_peak_high_return_pct'))}",
        f"- median_source_asof_to_peak_high_return_pct: {_fmt(stock_metrics.get('median_source_asof_to_peak_high_return_pct'))}",
        f"- avg_peak_high_to_post_week_close_pct: {_fmt(stock_metrics.get('avg_peak_high_to_post_week_close_pct'))}",
        f"- post_fade_le_neg10pct_rate: {_fmt(stock_metrics.get('post_fade_le_neg10pct_rate'))}",
        "",
        "## Peak Timing Bucket",
        "",
        _records_table(summary.get("peak_timing_bucket", []), "peak_timing_bucket"),
        "",
        "## Peak Gain Bucket",
        "",
        _records_table(summary.get("peak_gain_bucket", []), "peak_gain_bucket"),
        "",
        "## Post Peak Fade Bucket",
        "",
        _records_table(summary.get("post_peak_fade_bucket", []), "post_peak_fade_bucket"),
        "",
        "## Peak Window Pattern",
        "",
        _records_table(summary.get("peak_window_pattern", []), "peak_window_pattern"),
        "",
        "## Sector Summary",
        "",
        _records_table(summary.get("sector_summary", []), "sector"),
        "",
        "## Stock Peak Window Pattern",
        "",
        _records_table(summary.get("stock_peak_window_pattern", []), "peak_window_pattern"),
        "",
        "## Stock Sector Summary",
        "",
        _records_table(summary.get("stock_sector_summary", []), "sector"),
        "",
        f"promotion_decision={summary.get('promotion_decision', 'blocked_before_promotion_review')}",
        "",
    ]
    return "\n".join(lines)


def _records_table(records: list[dict[str, Any]], key: str) -> str:
    if not records:
        return "_No rows._"
    columns = [
        key,
        "rows",
        "row_share",
        "unique_stocks",
        "avg_asof_to_peak_high_return_pct",
        "avg_source_asof_to_peak_high_return_pct",
        "avg_peak_high_to_post_week_close_pct",
        "avg_forward_return_pct",
    ]
    available = [column for column in columns if column in records[0]]
    lines = ["| " + " | ".join(available) + " |", "| " + " | ".join(["---"] * len(available)) + " |"]
    for record in records:
        lines.append("| " + " | ".join(_fmt(record.get(column)) for column in available) + " |")
    return "\n".join(lines)


def _peak_timing_bucket(days_to_peak: int | float | None) -> str:
    value = _float(days_to_peak)
    if value is None:
        return ""
    if value <= 5:
        return "D01_05"
    if value <= 10:
        return "D06_10"
    if value <= 15:
        return "D11_15"
    return "D16_20"


def _peak_gain_bucket(value: float | None) -> str:
    number = _float(value)
    if number is None:
        return ""
    if number < 10:
        return "LT_10PCT"
    if number < 20:
        return "GAIN_10_20PCT"
    if number < 30:
        return "GAIN_20_30PCT"
    if number < 50:
        return "GAIN_30_50PCT"
    return "GAIN_GT_50PCT"


def _post_peak_fade_bucket(value: float | None) -> str:
    number = _float(value)
    if number is None:
        return ""
    if number <= -15:
        return "FADE_LE_NEG15PCT"
    if number <= -10:
        return "FADE_NEG10_15PCT"
    if number <= -5:
        return "FADE_NEG5_10PCT"
    if number < 0:
        return "FADE_NEG0_5PCT"
    return "HOLDS_OR_EXTENDS"


def _peak_window_pattern(
    *,
    trading_days_to_peak: int,
    peak_day_close_location_in_bar: float | None,
    peak_day_upper_shadow_pct: float | None,
    post_peak_fade_pct: float | None,
    peak_horizon_trading_days: int,
) -> str:
    location = _float(peak_day_close_location_in_bar)
    upper_shadow = _float(peak_day_upper_shadow_pct)
    fade = _float(post_peak_fade_pct)
    if trading_days_to_peak >= peak_horizon_trading_days - 2:
        return "CONTINUATION_INTO_WINDOW_END"
    if trading_days_to_peak <= 5 and fade is not None and fade <= -10:
        return "EARLY_SPIKE_FADE"
    if upper_shadow is not None and upper_shadow >= 45.0 and fade is not None and fade <= -5:
        return "SUPPLY_PRESSURE_PEAK"
    if location is not None and location >= 0.75 and fade is not None and fade > -5:
        return "STRONG_CLOSE_HOLDS_NEAR_HIGH"
    if fade is not None and fade <= -10:
        return "RUNUP_THEN_PULLBACK"
    return "NORMAL_PEAK_WINDOW"


def _upper_shadow_pct(row: pd.Series) -> float | None:
    high = _float(row.get("high"))
    low = _float(row.get("low"))
    open_ = _float(row.get("open"))
    close = _float(row.get("close"))
    if high is None or low is None or open_ is None or close is None:
        return None
    day_range = high - low
    if day_range <= 0:
        return 0.0
    return ((high - max(open_, close)) / day_range) * 100.0


def _pct(numerator: Any, denominator: Any) -> float | None:
    num = _float(numerator)
    den = _float(denominator)
    if num is None or den is None or den == 0:
        return None
    return ((num / den) - 1.0) * 100.0


def _ratio(numerator: Any, denominator: Any) -> float | None:
    num = _float(numerator)
    den = _float(denominator)
    if num is None or den is None or den == 0:
        return None
    return num / den


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _series_mean(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame.get(column), errors="coerce")
    if values.dropna().empty:
        return None
    return float(values.mean())


def _series_median(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame.get(column), errors="coerce")
    if values.dropna().empty:
        return None
    return float(values.median())


def _rate(mask: pd.Series) -> float | None:
    valid = mask.dropna()
    if valid.empty:
        return None
    return float(valid.mean())


def _round(value: Any, digits: int = 6) -> Any:
    number = _float(value)
    if number is None:
        return None
    return round(number, digits)


def _round_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: _round(value) for key, value in values.items()}


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output = output.replace([float("inf"), float("-inf")], pd.NA)
    for column in output.columns:
        if pd.api.types.is_numeric_dtype(output[column]):
            output[column] = output[column].round(6)
    return output.fillna("")


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_clean(item) for item in value]
    if isinstance(value, float):
        if pd.isna(value):
            return None
        return round(value, 6)
    if pd.isna(value) if value is not None and not isinstance(value, (str, bytes, list, dict)) else False:
        return None
    return value


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--screened-csv", default=DEFAULT_SCREENED_CSV)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--peak-horizon-trading-days", type=int, default=20)
    parser.add_argument("--context-trading-days", type=int, default=5)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
