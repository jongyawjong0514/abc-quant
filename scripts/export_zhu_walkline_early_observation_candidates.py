"""Export Zhu walkline early-observation candidates for manual labeling.

This is a shadow sidecar. It emits observation rows only and does not create
orders, positions, holdings, portfolio weights, or formal strategy state.
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

ALLOWED_MARKET_STATES = {
    "MARKET_STRONG_UPTREND",
    "MARKET_PULLBACK_IN_UPTREND",
    "MARKET_RANGE_BOUND",
}
ALLOWED_SECTOR_STATES = {
    "SECTOR_LEADING",
    "SECTOR_ROTATING_IN",
    "SECTOR_PULLBACK_HEALTHY",
}
EARLY_OUTPUT_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "close",
    "early_observation_rule",
    "review_bucket",
    "label_user",
    "rank_by_early_rule",
    "rank_by_rise",
    "rise_score",
    "grade",
    "fall_risk_score",
    "signal_stage",
    "trigger_type",
    "buy_observation_type",
    "buy_observation_detail_types",
    "buy_trigger_price",
    "buy_trigger_price_role",
    "confirm_price",
    "invalidation_price",
    "support_zone_1_label",
    "resistance_zone_1_label",
    "ma_state",
    "ma20",
    "ma20_slope",
    "ma120",
    "trend_state",
    "kline_state",
    "volume_state",
    "vol_ratio_20",
    "sector",
    "sector_rotation_rank",
    "sector_state",
    "market_state",
    "failure_type",
    "sell_warning_type",
    "stop_reference",
]
LABEL_TODO_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "close",
    "early_observation_rule",
    "review_bucket",
    "label_user",
    "support_zone_1_label",
    "resistance_zone_1_label",
]
DATE_STOCK_COLUMNS = ["asof_date", "stock_id", "stock_name", "label_user"]
_FAST_SELECTION_SUPPORT_COLUMNS = [
    "close_above_ma5",
    "close_above_ma20",
    "close_above_ma120",
    "support_zone_1_low",
    "support_zone_holding_today",
    "resistance_zone_breakout_today",
]


def main(argv: list[str] | None = None) -> int:
    from abc_quant.features.market_rotation import load_concept_stock_map
    from abc_quant.signals.zhu_walkline_shadow import build_zhu_walkline_shadow_result

    args = _parse_args(argv)
    config = _load_yaml(REPO_ROOT / args.config)
    sqlite_path = Path(config["data"]["sqlite_path"])
    trading_dates = _load_trading_dates(sqlite_path, args.start_date, args.end_date)
    if not trading_dates:
        raise ValueError(f"No trading dates found from {args.start_date} to {args.end_date}")

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.engine == "fast":
        full, daily = _run_fast_precomputed_engine(config, args, trading_dates)
        return _write_outputs(
            output_dir=output_dir,
            start_date=args.start_date,
            end_date=args.end_date,
            trading_dates=trading_dates,
            full=full,
            daily=daily,
            elapsed_seconds=float(daily["elapsed_seconds"].sum()) if not daily.empty else 0.0,
            args=args,
        )

    concept_map = load_concept_stock_map(REPO_ROOT / "config" / "concept_stock_map.yaml")
    base_bundle = _load_range_base_bundle(config, start_date=args.start_date, end_date=args.end_date)
    all_candidates: list[pd.DataFrame] = []
    daily_rows: list[dict[str, Any]] = []
    started_at = time.perf_counter()
    for index, asof_date in enumerate(trading_dates, start=1):
        day_start = time.perf_counter()
        bundle = _bundle_for_asof(base_bundle, asof_date)
        result = build_zhu_walkline_shadow_result(
            bundle,
            concept_map=concept_map,
            web_records=[],
            top_n=max(args.max_per_day, args.top_n_floor),
            web_research_used=False,
            config=config,
        )
        candidates = select_early_observation_candidates(
            result.feature_matrix,
            max_sector_rank=args.max_sector_rank,
            strict_fall_risk=args.strict_fall_risk,
            review_fall_risk=args.review_fall_risk,
            max_per_day=args.max_per_day,
        )
        if not candidates.empty:
            all_candidates.append(candidates)
        daily_rows.append(
            {
                "asof_date": asof_date,
                "mode": result.mode,
                "formal_champion_changed": result.formal_champion_changed,
                "formal_trade_effect": result.formal_trade_effect,
                "market_state": result.market.get("market_state", ""),
                "feature_count": len(result.feature_matrix),
                "candidate_count": len(candidates),
                "elapsed_seconds": round(time.perf_counter() - day_start, 3),
            }
        )
        if args.verbose:
            print(
                f"[{index}/{len(trading_dates)}] {asof_date} "
                f"candidates={len(candidates)} elapsed={daily_rows[-1]['elapsed_seconds']}s",
                flush=True,
            )

    full = pd.concat(all_candidates, ignore_index=True) if all_candidates else pd.DataFrame(columns=EARLY_OUTPUT_COLUMNS)
    daily = pd.DataFrame(daily_rows)
    return _write_outputs(
        output_dir=output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        trading_dates=trading_dates,
        full=full,
        daily=daily,
        elapsed_seconds=time.perf_counter() - started_at,
        args=args,
    )


def _write_outputs(
    *,
    output_dir: Path,
    start_date: str,
    end_date: str,
    trading_dates: list[str],
    full: pd.DataFrame,
    daily: pd.DataFrame,
    elapsed_seconds: float,
    args: argparse.Namespace,
) -> int:
    label_todo = full[LABEL_TODO_COLUMNS].copy() if not full.empty else pd.DataFrame(columns=LABEL_TODO_COLUMNS)
    date_stock_codes = (
        full[DATE_STOCK_COLUMNS].copy() if not full.empty else pd.DataFrame(columns=DATE_STOCK_COLUMNS)
    )
    summary = _summary_payload(
        start_date=start_date,
        end_date=end_date,
        trading_dates=trading_dates,
        candidates=full,
        daily=daily,
        elapsed_seconds=elapsed_seconds,
        args=args,
    )

    full_path = output_dir / "zhu_walkline_early_observation_candidates.csv"
    label_path = output_dir / "zhu_walkline_early_observation_label_todo.csv"
    date_stock_path = output_dir / "zhu_walkline_early_observation_date_stock_codes.csv"
    daily_path = output_dir / "zhu_walkline_early_observation_daily_counts.csv"
    summary_json_path = output_dir / "zhu_walkline_early_observation_summary.json"
    summary_md_path = output_dir / "zhu_walkline_early_observation_summary.md"
    full.to_csv(full_path, index=False, encoding="utf-8-sig")
    label_todo.to_csv(label_path, index=False, encoding="utf-8-sig")
    date_stock_codes.to_csv(date_stock_path, index=False, encoding="utf-8-sig")
    daily.to_csv(daily_path, index=False, encoding="utf-8-sig")
    summary_json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    summary_md_path.write_text(_summary_markdown(summary, label_todo), encoding="utf-8")

    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"candidate_csv={full_path}")
    print(f"label_todo_csv={label_path}")
    print(f"date_stock_codes_csv={date_stock_path}")
    print(f"daily_counts_csv={daily_path}")
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")
    return 0


def _run_fast_precomputed_engine(
    config: dict[str, Any],
    args: argparse.Namespace,
    trading_dates: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    started_at = time.perf_counter()
    sqlite_path = Path(config["data"]["sqlite_path"])
    price_rows = _load_precomputed_daily_rows(
        sqlite_path,
        start_date=args.start_date,
        end_date=args.end_date,
        lookback_days=args.fast_lookback_days,
    )
    if not args.include_etf_like:
        price_rows = price_rows[~price_rows["stock_id"].astype(str).str.startswith("00")].copy()
    stock_info = _load_stock_metadata(sqlite_path)
    feature_matrix = build_fast_precomputed_feature_matrix(
        price_rows,
        stock_info=stock_info,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    all_candidates: list[pd.DataFrame] = []
    daily_rows: list[dict[str, Any]] = []
    for index, asof_date in enumerate(trading_dates, start=1):
        day_start = time.perf_counter()
        day_features = feature_matrix[feature_matrix["asof_date"] == asof_date].copy()
        candidates = select_early_observation_candidates(
            day_features,
            max_sector_rank=args.max_sector_rank,
            strict_fall_risk=args.strict_fall_risk,
            review_fall_risk=args.review_fall_risk,
            max_per_day=args.max_per_day,
        )
        if not candidates.empty:
            all_candidates.append(candidates)
        market_state = ""
        if not day_features.empty:
            market_state = str(day_features["market_state"].dropna().iloc[0])
        daily_rows.append(
            {
                "asof_date": asof_date,
                "mode": "shadow_observation_only",
                "source_engine": "fast_precomputed_daily_ohlcv",
                "formal_champion_changed": False,
                "formal_trade_effect": False,
                "market_state": market_state,
                "feature_count": len(day_features),
                "candidate_count": len(candidates),
                "elapsed_seconds": round(time.perf_counter() - day_start, 3),
            }
        )
        if args.verbose:
            print(
                f"[{index}/{len(trading_dates)}] {asof_date} "
                f"fast_candidates={len(candidates)} elapsed={daily_rows[-1]['elapsed_seconds']}s",
                flush=True,
            )
    full = pd.concat(all_candidates, ignore_index=True) if all_candidates else pd.DataFrame(columns=EARLY_OUTPUT_COLUMNS)
    daily = pd.DataFrame(daily_rows)
    if not daily.empty:
        daily["elapsed_seconds"] = daily["elapsed_seconds"].astype(float)
        daily.loc[daily.index[-1], "elapsed_seconds"] += round(time.perf_counter() - started_at, 3)
    return full, daily


def build_fast_precomputed_feature_matrix(
    price_rows: pd.DataFrame,
    *,
    stock_info: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Build an as-of-safe fast feature matrix from precomputed OHLCV rows."""
    if price_rows.empty:
        return pd.DataFrame(columns=EARLY_OUTPUT_COLUMNS)
    data = price_rows.copy()
    data["date"] = pd.to_datetime(data["date"])
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    data = data[data["date"] <= end_ts].copy()
    data["stock_id"] = data["stock_id"].astype(str).str.zfill(4)
    data = data.sort_values(["stock_id", "date"]).reset_index(drop=True)
    grouped = data.groupby("stock_id", group_keys=False)
    data["prev_high"] = grouped["high"].shift(1)
    data["prev_low"] = grouped["low"].shift(1)
    data["prev_close_fast"] = grouped["close"].shift(1)
    data["prev_sma5"] = grouped["sma5"].shift(1)
    data["prev_sma10"] = grouped["sma10"].shift(1)
    data["prev_sma20"] = grouped["sma20"].shift(1)
    data["ma20_slope"] = data["sma20"] - data["prev_sma20"]
    data["ma120"] = grouped["close"].transform(
        lambda series: series.rolling(120, min_periods=120).mean()
    )
    data["high_20_prev"] = grouped["high"].transform(
        lambda series: series.rolling(20, min_periods=5).max().shift(1)
    )
    data["low_20_prev"] = grouped["low"].transform(
        lambda series: series.rolling(20, min_periods=5).min().shift(1)
    )
    data["high_60_prev"] = grouped["high"].transform(
        lambda series: series.rolling(60, min_periods=20).max().shift(1)
    )
    data["low_60_prev"] = grouped["low"].transform(
        lambda series: series.rolling(60, min_periods=20).min().shift(1)
    )
    data["prev_breakout_flag"] = (
        (data["close"] > data["high_20_prev"])
        & (data["close_location_in_bar"].fillna(0.5) >= 0.6)
    )
    data["recent_prior_breakout"] = grouped["prev_breakout_flag"].transform(
        lambda series: series.shift(1).rolling(5, min_periods=1).max().fillna(False)
    )
    data = data[(data["date"] >= start_ts) & (data["date"] <= end_ts)].copy()
    data = _attach_fast_stock_context(data, stock_info)
    data = _attach_fast_market_context(data)
    data = _attach_fast_signal_fields(data)
    data["ma20"] = data["sma20"]
    data["asof_date"] = data["date"].dt.strftime("%Y-%m-%d")
    for column in EARLY_OUTPUT_COLUMNS:
        if column not in data.columns:
            data[column] = ""
    return data[EARLY_OUTPUT_COLUMNS + _FAST_SELECTION_SUPPORT_COLUMNS].copy()


def _load_precomputed_daily_rows(
    sqlite_path: Path,
    *,
    start_date: str,
    end_date: str,
    lookback_days: int,
) -> pd.DataFrame:
    columns = [
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
        "range_pos_20",
        "sma5",
        "sma10",
        "sma20",
        "sma60",
        "sma5_gap",
        "sma10_gap",
        "sma20_gap",
        "sma60_gap",
        "volume_ma5",
        "volume_ma20",
        "day_volume_ratio_20",
        "intraday_return_rankpct",
        "sma20_gap_rankpct",
        "range_pos_20_rankpct",
        "day_volume_ratio_20_rankpct",
        "upper_tail_flag",
        "volume_exhaustion_flag",
        "late_chase_risk_flag",
    ]
    query = f"""
        select {", ".join(columns)}
        from daily_ohlcv_features
        where date >= date(?, ?)
          and date <= ?
          and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, f"-{lookback_days} day", end_date],
            parse_dates=["date"],
        )


def _load_stock_metadata(sqlite_path: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with sqlite3.connect(sqlite_path) as connection:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
        if "bigrich_industry_map" in tables:
            frames.append(
                pd.read_sql_query(
                    """
                    select stock_code as stock_id,
                           stock_name,
                           coalesce(industry_name, industry) as sector,
                           market,
                           1 as source_priority
                    from bigrich_industry_map
                    """,
                    connection,
                )
            )
        if "official_twse_company_basic" in tables:
            frames.append(
                pd.read_sql_query(
                    """
                    select 公司代號 as stock_id,
                           公司簡稱 as stock_name,
                           產業別 as sector,
                           'TWSE' as market,
                           2 as source_priority
                    from official_twse_company_basic
                    """,
                    connection,
                )
            )
        if "official_tpex_company_basic" in tables:
            frames.append(
                pd.read_sql_query(
                    """
                    select SecuritiesCompanyCode as stock_id,
                           CompanyAbbreviation as stock_name,
                           SecuritiesIndustryCode as sector,
                           'TPEx' as market,
                           3 as source_priority
                    from official_tpex_company_basic
                    """,
                    connection,
                )
            )
    if not frames:
        return pd.DataFrame(columns=["stock_id", "stock_name", "sector", "market"])
    metadata = pd.concat(frames, ignore_index=True)
    metadata["stock_id"] = metadata["stock_id"].astype(str).str.extract(r"(\d{4})", expand=False)
    metadata = metadata.dropna(subset=["stock_id"]).copy()
    metadata = metadata.sort_values(["stock_id", "source_priority"]).drop_duplicates("stock_id")
    return metadata[["stock_id", "stock_name", "sector", "market"]].reset_index(drop=True)


def _attach_fast_stock_context(data: pd.DataFrame, stock_info: pd.DataFrame) -> pd.DataFrame:
    if stock_info.empty:
        data["stock_name"] = ""
        data["sector"] = "UNKNOWN"
        return data
    merged = data.merge(stock_info, on="stock_id", how="left")
    merged["stock_name"] = merged["stock_name"].fillna("")
    merged["sector"] = merged["sector"].fillna("UNKNOWN")
    return merged


def _attach_fast_market_context(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["close_above_ma5"] = frame["close"] > frame["sma5"]
    frame["close_above_ma20"] = frame["close"] > frame["sma20"]
    frame["close_above_ma120"] = frame["close"] > frame["ma120"]
    frame["_sector_score"] = (
        frame["intraday_return_rankpct"].fillna(0.5) * 0.30
        + frame["sma20_gap_rankpct"].fillna(0.5) * 0.35
        + frame["range_pos_20_rankpct"].fillna(0.5) * 0.20
        + frame["day_volume_ratio_20_rankpct"].fillna(0.5) * 0.15
    )
    sector = (
        frame.groupby(["date", "sector"], dropna=False)
        .agg(sector_score=("_sector_score", "mean"), sector_member_count=("stock_id", "count"))
        .reset_index()
    )
    sector["sector_rotation_rank"] = sector.groupby("date")["sector_score"].rank(
        method="dense",
        ascending=False,
    )
    sector["sector_state"] = "SECTOR_LAGGING"
    sector.loc[sector["sector_rotation_rank"] <= 5, "sector_state"] = "SECTOR_LEADING"
    sector.loc[
        (sector["sector_rotation_rank"] > 5) & (sector["sector_rotation_rank"] <= 12),
        "sector_state",
    ] = "SECTOR_ROTATING_IN"
    frame = frame.merge(
        sector[["date", "sector", "sector_rotation_rank", "sector_state"]],
        on=["date", "sector"],
        how="left",
    )

    market = (
        frame.groupby("date")
        .agg(
            breadth_ma20=("close_above_ma20", "mean"),
            breadth_ma5=("close_above_ma5", "mean"),
            avg_sma20_gap=("sma20_gap", "mean"),
        )
        .reset_index()
    )
    market["market_state"] = "MARKET_DOWNTREND"
    market.loc[
        (market["breadth_ma20"] >= 0.55) & (market["avg_sma20_gap"] >= 0.0),
        "market_state",
    ] = "MARKET_STRONG_UPTREND"
    market.loc[
        (market["breadth_ma20"] >= 0.42)
        & (market["market_state"] == "MARKET_DOWNTREND"),
        "market_state",
    ] = "MARKET_RANGE_BOUND"
    market.loc[
        (market["breadth_ma20"] >= 0.32)
        & (market["breadth_ma5"] >= 0.36)
        & (market["market_state"] == "MARKET_DOWNTREND"),
        "market_state",
    ] = "MARKET_PULLBACK_IN_UPTREND"
    return frame.merge(
        market[["date", "market_state"]],
        on="date",
        how="left",
    )


def _attach_fast_signal_fields(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["close_above_ma5"] = frame["close"] > frame["sma5"]
    frame["close_above_ma20"] = frame["close"] > frame["sma20"]
    close_position = frame["close_location_in_bar"].fillna(0.5)
    volume_ratio = frame["day_volume_ratio_20"].fillna(0.0)
    upper_tail = frame["upper_tail_flag"].fillna(0).astype(bool)
    exhaustion = frame["volume_exhaustion_flag"].fillna(0).astype(bool)
    late_chase = frame["late_chase_risk_flag"].fillna(0).astype(bool)
    frame["support_zone_1_low"] = [
        _nearest_support(
            close=row.close,
            values=[row.prev_low, row.low_20_prev, row.sma5, row.sma10, row.sma20, row.low_60_prev],
        )
        for row in frame.itertuples(index=False)
    ]
    frame["_next_resistance"] = [
        _nearest_resistance(
            close=row.close,
            values=[row.prev_high, row.high_20_prev, row.sma5, row.sma10, row.sma20, row.sma60, row.high_60_prev],
        )
        for row in frame.itertuples(index=False)
    ]
    frame["support_zone_1_label"] = frame["support_zone_1_low"].map(_price_label)
    frame["resistance_zone_1_label"] = frame["_next_resistance"].map(_price_label)
    frame["invalidation_price"] = frame["support_zone_1_low"]
    frame["stop_reference"] = frame["support_zone_1_low"].map(
        lambda value: "" if _to_float(value) is None else f"訊號失效觀察價 {_price_label(value)}"
    )
    pressure_breakout = (
        (
            frame["close"] > frame["prev_high"].fillna(float("inf"))
        )
        | (
            (frame["high_20_prev"].notna())
            & (frame["close"] >= frame["high_20_prev"] * 0.995)
            & (frame["close"] > frame["prev_close_fast"].fillna(frame["close"]))
        )
    ) & (close_position >= 0.6) & (volume_ratio >= 0.55) & (~upper_tail)
    support_turn = (
        frame["support_zone_1_low"].notna()
        & (frame["low"] <= frame["support_zone_1_low"] * 1.015)
        & (frame["close"] >= frame["support_zone_1_low"])
        & (close_position >= 0.55)
        & (frame["close"] >= frame["prev_close_fast"].fillna(frame["close"]) * 0.995)
        & (~upper_tail)
    )
    resistance_turn_support = (
        frame["recent_prior_breakout"].fillna(False).astype(bool)
        & (frame["high_20_prev"].notna())
        & (frame["low"] <= frame["high_20_prev"] * 1.015)
        & (frame["close"] >= frame["high_20_prev"])
        & (~upper_tail)
    )
    ma_reclaim = (
        (
            (frame["close"] > frame["sma5"])
            & (frame["prev_close_fast"].fillna(frame["close"]) <= frame["prev_sma5"].fillna(frame["sma5"]))
        )
        | (
            (frame["close"] > frame["sma10"])
            & (frame["prev_close_fast"].fillna(frame["close"]) <= frame["prev_sma10"].fillna(frame["sma10"]))
        )
    ) & (close_position >= 0.55)

    frame["buy_observation_type"] = ""
    frame.loc[support_turn, "buy_observation_type"] = "SUPPORT_REBOUND"
    frame.loc[resistance_turn_support, "buy_observation_type"] = "RESISTANCE_TURN_SUPPORT"
    frame.loc[pressure_breakout, "buy_observation_type"] = "RESISTANCE_BREAKOUT"
    frame["buy_observation_detail_types"] = [
        "|".join(
            item
            for item, flag in [
                ("RESISTANCE_BREAKOUT", bool(breakout)),
                ("RESISTANCE_TURN_SUPPORT", bool(retest)),
                ("SUPPORT_REBOUND", bool(support)),
            ]
            if flag
        )
        for breakout, retest, support in zip(
            pressure_breakout,
            resistance_turn_support,
            support_turn,
            strict=False,
        )
    ]
    frame["resistance_zone_breakout_today"] = pressure_breakout
    frame["support_zone_holding_today"] = support_turn | resistance_turn_support
    frame["trigger_type"] = ""
    frame.loc[ma_reclaim, "trigger_type"] = "MA_RECLAIM"
    frame.loc[support_turn, "trigger_type"] = "PULLBACK_RESTART"
    frame.loc[pressure_breakout, "trigger_type"] = "RANGE_BREAKOUT"
    frame["ma_state"] = ""
    frame.loc[
        frame["close_above_ma5"] & (frame["close"] > frame["sma10"]) & frame["close_above_ma20"],
        "ma_state",
    ] = "BULL_ALIGNMENT"
    frame.loc[(ma_reclaim) & (frame["ma_state"] == ""), "ma_state"] = "MA_RECLAIM"
    frame.loc[
        (frame["close_above_ma5"]) & (frame["close"] > frame["sma10"]) & (frame["ma_state"] == ""),
        "ma_state",
    ] = "MA_COMPRESSION"
    frame["trend_state"] = "RANGE"
    frame.loc[frame["close"] > frame["sma20"], "trend_state"] = "UPTREND"
    frame.loc[frame["close"] < frame["sma20"] * 0.97, "trend_state"] = "DOWNTREND"
    frame["kline_state"] = "NEUTRAL_K"
    frame.loc[close_position >= 0.7, "kline_state"] = "ATTACK_RED_K"
    frame.loc[upper_tail, "kline_state"] = "UPPER_SHADOW_SUPPLY"
    frame["volume_state"] = "NORMAL_VOLUME"
    frame.loc[volume_ratio >= 1.2, "volume_state"] = "ATTACK_VOLUME"
    frame.loc[volume_ratio < 0.75, "volume_state"] = "LOW_VOLUME"
    frame["vol_ratio_20"] = volume_ratio.round(4)
    frame["fall_risk_score"] = (
        upper_tail.astype(int) * 18
        + exhaustion.astype(int) * 12
        + late_chase.astype(int) * 10
        + (~frame["close_above_ma20"]).astype(int) * 12
        + ((volume_ratio >= 1.8) & (close_position < 0.6)).astype(int) * 10
    ).clip(0, 90)
    frame["rise_score"] = (
        35
        + pressure_breakout.astype(int) * 23
        + resistance_turn_support.astype(int) * 19
        + support_turn.astype(int) * 14
        + ma_reclaim.astype(int) * 10
        + frame["close_above_ma20"].astype(int) * 8
        + (volume_ratio >= 1.0).astype(int) * 6
        + (frame["range_pos_20"].fillna(0.0) >= 0.65).astype(int) * 5
        + (13 - frame["sector_rotation_rank"].fillna(13)).clip(lower=0)
    ).clip(0, 100)
    frame["grade"] = "C"
    frame.loc[frame["rise_score"] >= 60, "grade"] = "B"
    frame.loc[frame["rise_score"] >= 80, "grade"] = "A"
    frame["signal_stage"] = "SETUP"
    frame.loc[ma_reclaim | support_turn, "signal_stage"] = "TRIGGER"
    frame.loc[pressure_breakout | resistance_turn_support, "signal_stage"] = "CONFIRMED"
    warning = upper_tail | exhaustion | late_chase
    frame["failure_type"] = ""
    frame.loc[upper_tail | exhaustion, "failure_type"] = "SUPPLY_PRESSURE"
    frame.loc[late_chase & (frame["failure_type"] == ""), "failure_type"] = "MARGIN_CROWDING"
    frame["sell_warning_type"] = ""
    frame.loc[warning, "sell_warning_type"] = "RESISTANCE_REJECTION"
    frame["buy_trigger_price"] = frame["_next_resistance"]
    frame.loc[pressure_breakout | support_turn | resistance_turn_support | ma_reclaim, "buy_trigger_price"] = frame[
        "close"
    ]
    frame["buy_trigger_price_role"] = "EMPTY"
    frame.loc[frame["buy_trigger_price"].notna(), "buy_trigger_price_role"] = "NEXT_CONFIRMATION_PRICE"
    frame.loc[frame["buy_observation_type"] != "", "buy_trigger_price_role"] = "TRIGGERED_PRICE"
    frame["confirm_price"] = frame["_next_resistance"]
    for column in [
        "buy_trigger_price",
        "confirm_price",
        "invalidation_price",
        "support_zone_1_low",
        "sector_rotation_rank",
        "rise_score",
        "fall_risk_score",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").round(4)
    return frame


def select_early_observation_candidates(
    feature_matrix: pd.DataFrame,
    *,
    max_sector_rank: int = 12,
    strict_fall_risk: float = 35.0,
    review_fall_risk: float = 45.0,
    max_per_day: int | None = 30,
) -> pd.DataFrame:
    """Return early walkline observation rows for manual labels."""
    if feature_matrix.empty:
        return pd.DataFrame(columns=EARLY_OUTPUT_COLUMNS)
    frame = feature_matrix.copy()
    derived_columns = {
        "early_observation_rule",
        "review_bucket",
        "label_user",
        "rank_by_early_rule",
        "rank_by_rise",
    }
    frame = frame.drop(columns=[column for column in derived_columns if column in frame.columns])
    for column in [name for name in EARLY_OUTPUT_COLUMNS if name not in derived_columns]:
        if column not in frame.columns:
            frame[column] = ""
    frame["_rank_by_rise"] = frame["rise_score"].map(_number_or_negative).rank(
        method="first",
        ascending=False,
    )
    annotated = frame.apply(
        lambda row: _early_rule_for_row(
            row,
            max_sector_rank=max_sector_rank,
            strict_fall_risk=strict_fall_risk,
            review_fall_risk=review_fall_risk,
        ),
        axis=1,
        result_type="expand",
    )
    annotated.columns = ["early_observation_rule", "review_bucket"]
    output = pd.concat([frame, annotated], axis=1)
    output = output[output["early_observation_rule"] != ""].copy()
    if output.empty:
        return pd.DataFrame(columns=EARLY_OUTPUT_COLUMNS)
    output["rank_by_rise"] = output["_rank_by_rise"].astype(int)
    output["rank_by_early_rule"] = (
        output["early_observation_rule"].map(_rule_priority).astype(int) * 10_000
        + output["fall_risk_score"].map(_number_or_large)
        - output["rise_score"].map(_number_or_negative)
    ).rank(method="first", ascending=True).astype(int)
    output["label_user"] = ""
    output = output.sort_values(
        ["rank_by_early_rule", "rise_score", "fall_risk_score"],
        ascending=[True, False, True],
    )
    if max_per_day is not None and max_per_day > 0:
        output = output.head(max_per_day)
    return output[EARLY_OUTPUT_COLUMNS].map(_clean_output_value)


def _load_range_base_bundle(config: dict[str, Any], *, start_date: str, end_date: str) -> Any:
    from abc_quant.data.local_tw_loader import LocalTwDataBundle, load_local_tw_bundle

    base = load_local_tw_bundle(config, asof=end_date)
    sqlite_path = Path(config["data"]["sqlite_path"])
    chip = _load_range_table(
        sqlite_path,
        table_name="tw_official_institutional_trading_daily",
        date_column="trade_date",
        start_date=start_date,
        end_date=end_date,
        start_modifier="-45 day",
        parse_dates=["trade_date"],
        fallback=base.chip_history,
    )
    margin = _load_range_table(
        sqlite_path,
        table_name="tw_margin_balance_history",
        date_column="trade_date",
        start_date=start_date,
        end_date=end_date,
        start_modifier="-45 day",
        parse_dates=["trade_date"],
        fallback=base.margin_history,
    )
    holder = _load_range_table(
        sqlite_path,
        table_name="latest_tw_tdcc_holder_moving_averages",
        date_column="date",
        start_date=start_date,
        end_date=end_date,
        start_modifier="-180 day",
        parse_dates=["date"],
        fallback=base.holder_latest,
    )
    return LocalTwDataBundle(
        asof_date=base.asof_date,
        requested_asof=base.requested_asof,
        price_history=base.price_history,
        stock_info=base.stock_info,
        chip_history=chip,
        margin_history=margin,
        holder_latest=holder,
        market_history=base.market_history,
        sector_sentiment=base.sector_sentiment,
        stock_context=base.stock_context,
        class_membership=base.class_membership,
        data_quality=base.data_quality,
    )


def _bundle_for_asof(base_bundle: Any, asof_date: str) -> Any:
    from abc_quant.data.local_tw_loader import LocalTwDataBundle

    return LocalTwDataBundle(
        asof_date=asof_date,
        requested_asof=asof_date,
        price_history=base_bundle.price_history,
        stock_info=base_bundle.stock_info,
        chip_history=base_bundle.chip_history,
        margin_history=base_bundle.margin_history,
        holder_latest=base_bundle.holder_latest,
        market_history=base_bundle.market_history,
        sector_sentiment=base_bundle.sector_sentiment,
        stock_context=base_bundle.stock_context,
        class_membership=base_bundle.class_membership,
        data_quality=base_bundle.data_quality,
    )


def _load_range_table(
    sqlite_path: Path,
    *,
    table_name: str,
    date_column: str,
    start_date: str,
    end_date: str,
    start_modifier: str,
    parse_dates: list[str],
    fallback: pd.DataFrame,
) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        exists = connection.execute(
            "select 1 from sqlite_master where type='table' and name=?",
            (table_name,),
        ).fetchone()
        if not exists:
            return fallback
        query = f"""
            select *
            from {table_name}
            where {date_column} >= date(?, ?)
              and {date_column} <= ?
        """
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, start_modifier, end_date],
            parse_dates=parse_dates,
        )


def _early_rule_for_row(
    row: pd.Series,
    *,
    max_sector_rank: int,
    strict_fall_risk: float,
    review_fall_risk: float,
) -> tuple[str, str]:
    if str(row.get("market_state", "")) not in ALLOWED_MARKET_STATES:
        return "", ""
    sector_rank = _to_float(row.get("sector_rotation_rank"))
    if sector_rank is None or sector_rank > max_sector_rank:
        return "", ""
    sector_state = str(row.get("sector_state", ""))
    if sector_state and sector_state not in ALLOWED_SECTOR_STATES:
        return "", ""
    if not _to_bool(row.get("close_above_ma5")):
        return "", ""
    if not _to_bool(row.get("close_above_ma20")):
        return "", ""
    if not _to_bool(row.get("close_above_ma120")):
        return "", ""
    if _to_float(row.get("support_zone_1_low")) is None and _to_float(row.get("invalidation_price")) is None:
        return "", ""
    ma20_slope = _to_float(row.get("ma20_slope"))
    if ma20_slope is None or ma20_slope <= 0:
        return "", ""
    fall_risk = _to_float(row.get("fall_risk_score")) or 0.0
    if fall_risk >= review_fall_risk:
        return "", ""

    type_tokens = _split_types(row.get("buy_observation_detail_types"))
    buy_type = str(row.get("buy_observation_type", "") or "")
    trigger = str(row.get("trigger_type", "") or "")
    ma_state = str(row.get("ma_state", "") or "")
    close_above_ma20 = _to_bool(row.get("close_above_ma20"))
    trend_repaired = close_above_ma20 or ma_state in {"MA_RECLAIM", "MA_COMPRESSION", "BULL_ALIGNMENT"}
    pressure_breakout = (
        buy_type == "RESISTANCE_BREAKOUT"
        or "RESISTANCE_BREAKOUT" in type_tokens
        or _to_bool(row.get("resistance_zone_breakout_today"))
    )
    support_turn = (
        buy_type in {"RESISTANCE_TURN_SUPPORT", "FAILED_BREAKDOWN_RECLAIM", "SUPPORT_REBOUND"}
        or bool({"RESISTANCE_TURN_SUPPORT", "FAILED_BREAKDOWN_RECLAIM", "SUPPORT_REBOUND"} & type_tokens)
        or _to_bool(row.get("support_zone_holding_today"))
    )
    ma_reclaim = trigger == "MA_RECLAIM" or ma_state == "MA_RECLAIM"

    if pressure_breakout and close_above_ma20 and fall_risk < strict_fall_risk:
        return "STRICT_BREAKOUT", _review_bucket(row)
    if support_turn and close_above_ma20 and fall_risk < strict_fall_risk:
        return "STRICT_SUPPORT_TURN", _review_bucket(row)
    if ma_reclaim and trend_repaired:
        return "AGGRESSIVE_MA_RECLAIM_REVIEW", _review_bucket(row)
    if pressure_breakout and trend_repaired:
        return "AGGRESSIVE_BREAKOUT_REVIEW", _review_bucket(row)
    if support_turn and trend_repaired:
        return "AGGRESSIVE_SUPPORT_REVIEW", _review_bucket(row)
    return "", ""


def _review_bucket(row: pd.Series) -> str:
    warnings: list[str] = []
    if str(row.get("signal_stage", "")) == "FAILED":
        warnings.append("SIGNAL_FAILED")
    if str(row.get("sell_warning_type", "")):
        warnings.append("SELL_WARNING")
    failure_type = str(row.get("failure_type", "") or "")
    if failure_type:
        warnings.append("FAILURE_TAG")
    if "NO_VOLUME_FOLLOW" in failure_type:
        warnings.append("NO_VOLUME_FOLLOW")
    fall_risk = _to_float(row.get("fall_risk_score"))
    if fall_risk is not None and fall_risk >= 35:
        warnings.append("HIGHER_RISK_REVIEW")
    return "REVIEW_WITH_WARNING:" + "|".join(warnings) if warnings else "CLEAN_REVIEW"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--max-per-day", type=int, default=30)
    parser.add_argument("--max-sector-rank", type=int, default=12)
    parser.add_argument("--strict-fall-risk", type=float, default=35.0)
    parser.add_argument("--review-fall-risk", type=float, default=45.0)
    parser.add_argument("--top-n-floor", type=int, default=30)
    parser.add_argument(
        "--engine",
        choices=["exact", "fast"],
        default="exact",
        help="exact uses the full Zhu scanner; fast uses precomputed daily OHLCV for manual labels.",
    )
    parser.add_argument("--fast-lookback-days", type=int, default=260)
    parser.add_argument(
        "--include-etf-like",
        action="store_true",
        help="Include 00xx ETF-like tickers in the fast manual-label export.",
    )
    parser.add_argument("--output-dir", default="reports/zhu_walkline_early_observation_labels")
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


def _summary_payload(
    *,
    start_date: str,
    end_date: str,
    trading_dates: list[str],
    candidates: pd.DataFrame,
    daily: pd.DataFrame,
    elapsed_seconds: float,
    args: argparse.Namespace,
) -> dict[str, Any]:
    rule_counts = (
        candidates["early_observation_rule"].value_counts().sort_index().to_dict()
        if not candidates.empty
        else {}
    )
    return {
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "purpose": "manual_labeling_sidecar",
        "source_engine": "fast_precomputed_daily_ohlcv" if args.engine == "fast" else "exact_scanner",
        "start_date": start_date,
        "end_date": end_date,
        "resolved_start_date": trading_dates[0] if trading_dates else None,
        "resolved_end_date": trading_dates[-1] if trading_dates else None,
        "trading_days": len(trading_dates),
        "candidate_rows": int(len(candidates)),
        "unique_stocks": int(candidates["stock_id"].nunique()) if not candidates.empty else 0,
        "non_empty_days": int((daily["candidate_count"] > 0).sum()) if not daily.empty else 0,
        "max_per_day": int(args.max_per_day),
        "max_sector_rank": int(args.max_sector_rank),
        "strict_fall_risk": float(args.strict_fall_risk),
        "review_fall_risk": float(args.review_fall_risk),
        "fast_lookback_days": int(args.fast_lookback_days),
        "include_etf_like": bool(args.include_etf_like),
        "rule_counts": {str(key): int(value) for key, value in rule_counts.items()},
        "elapsed_seconds": round(elapsed_seconds, 3),
        "no_formal_strategy_modified": True,
        "no_formal_champion_modified": True,
        "no_formal_trade_effect": True,
    }


def _summary_markdown(summary: dict[str, Any], label_todo: pd.DataFrame) -> str:
    preview = label_todo.head(60)
    lines = [
        "# Zhu Walkline Early Observation Label Export",
        "",
        "本輸出是 shadow observation 人工標註 sidecar，不是買進名單，不是交易指令。",
        "",
        f"- range: `{summary['start_date']}` to `{summary['end_date']}`",
        f"- resolved trading days: {summary['trading_days']}",
        f"- candidate rows: {summary['candidate_rows']}",
        f"- unique stocks: {summary['unique_stocks']}",
        f"- non-empty days: {summary['non_empty_days']}",
        f"- rule counts: `{summary['rule_counts']}`",
        f"- source engine: `{summary['source_engine']}`",
        "",
        "## Label Preview",
        "",
        _markdown_table(preview, LABEL_TODO_COLUMNS),
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


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    selected = frame[columns].copy()
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in selected.iterrows():
        lines.append("| " + " | ".join(str(_clean_output_value(row[column])) for column in columns) + " |")
    return "\n".join(lines)


def _nearest_support(*, close: Any, values: list[Any]) -> float | None:
    close_number = _to_float(close)
    if close_number is None:
        return None
    candidates = [
        value
        for value in (_to_float(item) for item in values)
        if value is not None and value > 0 and value <= close_number * 1.003
    ]
    if not candidates:
        return None
    return max(candidates)


def _nearest_resistance(*, close: Any, values: list[Any]) -> float | None:
    close_number = _to_float(close)
    if close_number is None:
        return None
    candidates = [
        value
        for value in (_to_float(item) for item in values)
        if value is not None and value > close_number * 1.003
    ]
    if not candidates:
        return None
    return min(candidates)


def _price_label(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return ""
    if abs(number) >= 100:
        return f"{number:.1f}".rstrip("0").rstrip(".")
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _rule_priority(value: str) -> int:
    priorities = {
        "STRICT_BREAKOUT": 1,
        "STRICT_SUPPORT_TURN": 2,
        "AGGRESSIVE_MA_RECLAIM_REVIEW": 3,
        "AGGRESSIVE_BREAKOUT_REVIEW": 4,
        "AGGRESSIVE_SUPPORT_REVIEW": 5,
    }
    return priorities.get(str(value), 99)


def _split_types(value: Any) -> set[str]:
    return {item.strip() for item in str(value or "").split("|") if item.strip()}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _number_or_negative(value: Any) -> float:
    number = _to_float(value)
    return number if number is not None else -1.0


def _number_or_large(value: Any) -> float:
    number = _to_float(value)
    return number if number is not None else 999.0


def _clean_output_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if pd.isna(value):
        return ""
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
