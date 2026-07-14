"""Compare exact T-5, T-3, and T-1 snapshots before KD D+5 signals.

All snapshot fields come from adjusted OHLCV rows strictly before the signal
date. Forward D+5 returns are evaluator-only group labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LEAD_OFFSETS = (5, 3, 1)
GROUP_ORDER = {"D5_LOSS": 1, "D5_GAIN_10_20": 2, "D5_GAIN_GE_20": 3}
GROUP_LABELS = {
    "D5_LOSS": "D+5 < 0%",
    "D5_GAIN_10_20": "D+5 +10% to <20%",
    "D5_GAIN_GE_20": "D+5 >=20%",
}
NUMERIC_FEATURES = (
    "daily_return_pct",
    "return_5d_pct",
    "return_20d_pct",
    "close_to_sma5_pct",
    "close_to_sma20_pct",
    "close_to_sma60_pct",
    "sma20_slope_5d_pct",
    "sma60_slope_5d_pct",
    "day_volume_ratio_20",
    "close_location_in_bar",
    "range_pos_20",
    "open_to_close_pct",
    "kd_k9",
    "kd_d9",
    "kd_spread",
    "kd_k_change_1d",
)
CONDITIONS = (
    "red_k",
    "close_above_sma20",
    "close_above_sma60",
    "sma20_slope_positive",
    "sma60_slope_positive",
    "return_20d_positive",
    "kd_k_rising",
    "kd_above_d",
    "kd_oversold",
    "quiet_volume",
    "expanded_volume",
    "close_high_in_bar",
    "strong_uptrend",
)
FEATURE_LABELS = {
    "daily_return_pct": "當日報酬(%)",
    "return_5d_pct": "截至該日5日報酬(%)",
    "return_20d_pct": "截至該日20日報酬(%)",
    "close_to_sma5_pct": "收盤相對5日線(%)",
    "close_to_sma20_pct": "收盤相對月線(%)",
    "close_to_sma60_pct": "收盤相對季線(%)",
    "sma20_slope_5d_pct": "月線5日斜率(%)",
    "sma60_slope_5d_pct": "季線5日斜率(%)",
    "day_volume_ratio_20": "20日量比",
    "close_location_in_bar": "收盤K棒位置",
    "range_pos_20": "20日區間位置",
    "open_to_close_pct": "開收到收盤漲跌(%)",
    "kd_k9": "K(9)",
    "kd_d9": "D(9)",
    "kd_spread": "K-D",
    "kd_k_change_1d": "K單日變化",
}
CONDITION_LABELS = {
    "red_k": "紅K",
    "close_above_sma20": "站上月線",
    "close_above_sma60": "站上季線",
    "sma20_slope_positive": "月線斜率>0",
    "sma60_slope_positive": "季線斜率>0",
    "return_20d_positive": "20日報酬>0",
    "kd_k_rising": "K向上",
    "kd_above_d": "K>D",
    "kd_oversold": "K<20",
    "quiet_volume": "量比<=0.75",
    "expanded_volume": "量比>=1.2",
    "close_high_in_bar": "收在K棒上半部",
    "strong_uptrend": "站上月季線且月季線斜率>0",
}


def prepare_adjusted_history(history: pd.DataFrame) -> pd.DataFrame:
    """Calculate adjusted point-in-time indicators for each stock."""
    if history.empty:
        return history.copy()
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["stock_id"] = data["stock_id"].astype(str).str.zfill(4)
    data = data.dropna(subset=["date"]).sort_values(["stock_id", "date"])
    parts: list[pd.DataFrame] = []
    for _stock_id, group in data.groupby("stock_id", sort=False):
        values = group.copy()
        for column in ["adj_open", "adj_high", "adj_low", "adj_close", "volume"]:
            values[column] = pd.to_numeric(values[column], errors="coerce")
        close = values["adj_close"]
        high = values["adj_high"]
        low = values["adj_low"]
        grouped_sma = {window: close.rolling(window, min_periods=window).mean() for window in (5, 20, 60)}
        values["daily_return_pct"] = close.pct_change() * 100.0
        values["return_5d_pct"] = close.pct_change(5) * 100.0
        values["return_20d_pct"] = close.pct_change(20) * 100.0
        for window, sma in grouped_sma.items():
            values[f"sma{window}"] = sma
            values[f"close_to_sma{window}_pct"] = (close / sma - 1.0) * 100.0
        values["sma20_slope_5d_pct"] = grouped_sma[20].pct_change(5) * 100.0
        values["sma60_slope_5d_pct"] = grouped_sma[60].pct_change(5) * 100.0
        values["day_volume_ratio_20"] = values["volume"] / values["volume"].rolling(
            20, min_periods=20
        ).mean()
        span = high - low
        values["close_location_in_bar"] = ((close - low) / span).where(span.ne(0), 0.5)
        rolling_low = low.rolling(20, min_periods=20).min()
        rolling_high = high.rolling(20, min_periods=20).max()
        range_span = rolling_high - rolling_low
        values["range_pos_20"] = ((close - rolling_low) / range_span).where(
            range_span.ne(0), 0.5
        )
        values["open_to_close_pct"] = (close / values["adj_open"] - 1.0) * 100.0
        low9 = low.rolling(9, min_periods=1).min()
        high9 = high.rolling(9, min_periods=1).max()
        span9 = high9 - low9
        rsv = (((close - low9) * 100.0) / span9).where(span9.ne(0), 50.0).clip(0, 100)
        kd_k, kd_d = _smoothed_kd(rsv)
        values["kd_k9"] = kd_k
        values["kd_d9"] = kd_d
        values["kd_spread"] = kd_k - kd_d
        values["kd_k_change_1d"] = kd_k.diff()
        parts.append(values)
    return pd.concat(parts, ignore_index=True).sort_values(["stock_id", "date"])


def build_lead_snapshots(
    signals: pd.DataFrame,
    history: pd.DataFrame,
    *,
    offsets: tuple[int, ...] = LEAD_OFFSETS,
) -> pd.DataFrame:
    """Return exact prior-trading-day snapshots for every signal."""
    events = signals.copy()
    events["asof_date"] = pd.to_datetime(events["asof_date"], errors="coerce")
    events["stock_id"] = events["stock_id"].astype(str).str.zfill(4)
    feature_history = prepare_adjusted_history(history)
    groups = {
        stock_id: group.reset_index(drop=True)
        for stock_id, group in feature_history.groupby("stock_id", sort=False)
    }
    records: list[dict[str, Any]] = []
    for event in events.itertuples(index=False):
        stock_id = str(event.stock_id)
        signal_date = pd.Timestamp(event.asof_date)
        stock_history = groups.get(stock_id, pd.DataFrame())
        prior = stock_history[stock_history["date"] < signal_date]
        event_values = event._asdict()
        for offset in offsets:
            row: dict[str, Any] = {
                "asof_date": signal_date.strftime("%Y-%m-%d"),
                "stock_id": stock_id,
                "lead_offset": int(offset),
                "lead_label": f"T-{offset}",
            }
            for column in [
                "stock_name",
                "d5_group",
                "d5_group_label",
                "d5_adjusted_return_pct",
                "corporate_action_event_in_horizon",
            ]:
                row[column] = event_values.get(column)
            if len(prior) >= offset:
                snapshot = prior.iloc[-offset]
                row["feature_date"] = pd.Timestamp(snapshot["date"]).strftime("%Y-%m-%d")
                row["adj_close"] = snapshot.get("adj_close")
                for feature in NUMERIC_FEATURES:
                    row[feature] = snapshot.get(feature)
                row.update(_condition_values(snapshot))
            else:
                row["feature_date"] = ""
                row["adj_close"] = np.nan
                for feature in NUMERIC_FEATURES:
                    row[feature] = np.nan
                for condition in CONDITIONS:
                    row[condition] = np.nan
            records.append(row)
    output = pd.DataFrame(records)
    assert_no_lookahead(output)
    return output


def build_group_stats(rows: pd.DataFrame, *, scope: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for (offset, group_key), group in rows.groupby(["lead_offset", "d5_group"], sort=False):
        for feature in NUMERIC_FEATURES:
            values = pd.to_numeric(group[feature], errors="coerce").dropna()
            records.append(
                {
                    "scope": scope,
                    "lead_offset": int(offset),
                    "lead_label": f"T-{offset}",
                    "d5_group": group_key,
                    "d5_group_order": GROUP_ORDER[group_key],
                    "feature": feature,
                    "feature_label": FEATURE_LABELS[feature],
                    "rows": int(len(group)),
                    "available_rows": int(len(values)),
                    "coverage": len(values) / len(group) if len(group) else 0.0,
                    "mean": values.mean() if not values.empty else np.nan,
                    "median": values.median() if not values.empty else np.nan,
                    "q25": values.quantile(0.25) if not values.empty else np.nan,
                    "q75": values.quantile(0.75) if not values.empty else np.nan,
                }
            )
    return _round_numeric(pd.DataFrame(records))


def build_condition_shares(rows: pd.DataFrame, *, scope: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for (offset, group_key), group in rows.groupby(["lead_offset", "d5_group"], sort=False):
        for condition in CONDITIONS:
            values = group[condition].dropna().astype(bool)
            records.append(
                {
                    "scope": scope,
                    "lead_offset": int(offset),
                    "lead_label": f"T-{offset}",
                    "d5_group": group_key,
                    "d5_group_order": GROUP_ORDER[group_key],
                    "condition": condition,
                    "condition_label": CONDITION_LABELS[condition],
                    "rows": int(len(group)),
                    "available_rows": int(len(values)),
                    "share": values.mean() if not values.empty else np.nan,
                }
            )
    return _round_numeric(pd.DataFrame(records))


def build_pairwise(rows: pd.DataFrame, *, scope: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for offset in LEAD_OFFSETS:
        at_offset = rows[rows["lead_offset"].eq(offset)]
        loss = at_offset[at_offset["d5_group"].eq("D5_LOSS")]
        for target_key in ("D5_GAIN_10_20", "D5_GAIN_GE_20"):
            target = at_offset[at_offset["d5_group"].eq(target_key)]
            for feature in NUMERIC_FEATURES:
                target_values = pd.to_numeric(target[feature], errors="coerce").dropna()
                loss_values = pd.to_numeric(loss[feature], errors="coerce").dropna()
                if target_values.empty or loss_values.empty:
                    continue
                pooled_std = np.sqrt(
                    (target_values.var(ddof=0) + loss_values.var(ddof=0)) / 2.0
                )
                mean_diff = target_values.mean() - loss_values.mean()
                records.append(
                    {
                        "scope": scope,
                        "lead_offset": offset,
                        "lead_label": f"T-{offset}",
                        "target_group": target_key,
                        "reference_group": "D5_LOSS",
                        "feature": feature,
                        "feature_label": FEATURE_LABELS[feature],
                        "target_median": target_values.median(),
                        "reference_median": loss_values.median(),
                        "median_difference": target_values.median() - loss_values.median(),
                        "mean_difference": mean_diff,
                        "standardized_mean_difference": (
                            mean_diff / pooled_std
                            if pooled_std and pd.notna(pooled_std)
                            else 0.0
                        ),
                    }
                )
    return _round_numeric(pd.DataFrame(records))


def build_trajectories(rows: pd.DataFrame) -> pd.DataFrame:
    keys = ["asof_date", "stock_id", "stock_name", "d5_group", "d5_group_label"]
    records: list[dict[str, Any]] = []
    for key, group in rows.groupby(keys, dropna=False, sort=False):
        indexed = group.set_index("lead_offset")
        if 5 not in indexed.index or 1 not in indexed.index:
            continue
        start = indexed.loc[5]
        end = indexed.loc[1]
        record = dict(zip(keys, key, strict=True))
        record.update(
            {
                "t5_to_t1_return_pct": _pct_change(start["adj_close"], end["adj_close"]),
                "t5_to_t1_k_change": _difference(start["kd_k9"], end["kd_k9"]),
                "t5_to_t1_volume_ratio_change": _difference(
                    start["day_volume_ratio_20"], end["day_volume_ratio_20"]
                ),
                "t5_to_t1_ma20_gap_change_pctpt": _difference(
                    start["close_to_sma20_pct"], end["close_to_sma20_pct"]
                ),
            }
        )
        records.append(record)
    return _round_numeric(pd.DataFrame(records))


def build_early_stage_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Build prespecified early-stage flags without using D+5 outcomes."""
    keys = [
        "asof_date",
        "stock_id",
        "stock_name",
        "d5_group",
        "d5_group_label",
        "d5_adjusted_return_pct",
        "same_stock_cooldown",
        "corporate_action_event_in_horizon",
    ]
    records: list[dict[str, Any]] = []
    for key, group in rows.groupby(keys, dropna=False, sort=False):
        indexed = group.set_index("lead_offset")
        if not all(offset in indexed.index for offset in LEAD_OFFSETS):
            continue
        t5 = indexed.loc[5]
        t3 = indexed.loc[3]
        t1 = indexed.loc[1]
        record = dict(zip(keys, key, strict=True))
        record.update(
            {
                "t5_quiet_setup": _number(t5["day_volume_ratio_20"]) <= 0.75,
                "t3_price_turn": _number(t3["daily_return_pct"]) > 0.0,
                "t1_price_confirm": _number(t1["daily_return_pct"]) > 0.0,
                "t1_volume_confirm": _number(t1["day_volume_ratio_20"]) >= 0.70,
                "t5_volume_ratio": t5["day_volume_ratio_20"],
                "t3_daily_return_pct": t3["daily_return_pct"],
                "t1_daily_return_pct": t1["daily_return_pct"],
                "t1_volume_ratio": t1["day_volume_ratio_20"],
            }
        )
        record["early_stage_score"] = 25 * sum(
            bool(record[column])
            for column in [
                "t5_quiet_setup",
                "t3_price_turn",
                "t1_price_confirm",
                "t1_volume_confirm",
            ]
        )
        record["early_stage"] = _early_stage(record)
        records.append(record)
    return pd.DataFrame(records)


def evaluate_early_stage_rules(
    rows: pd.DataFrame,
    *,
    holdout_start: str = "2026-04-01",
) -> pd.DataFrame:
    """Evaluate prespecified stages on the de-overlapped Apr-Jun sample."""
    data = rows.copy()
    data["asof_date"] = pd.to_datetime(data["asof_date"], errors="coerce")
    holdout = data[
        data["asof_date"].ge(pd.Timestamp(holdout_start))
        & data["same_stock_cooldown"].astype(bool)
        & (~data["corporate_action_event_in_horizon"].astype(bool))
    ].copy()
    masks = {
        "BASELINE_ALL": pd.Series(True, index=holdout.index),
        "T5_SETUP": holdout["t5_quiet_setup"],
        "T3_EARLY_TURN": holdout["t5_quiet_setup"] & holdout["t3_price_turn"],
        "T1_PRICE_CONFIRM": (
            holdout["t5_quiet_setup"]
            & holdout["t3_price_turn"]
            & holdout["t1_price_confirm"]
        ),
        "T1_PRICE_VOLUME_CONFIRM": (
            holdout["t5_quiet_setup"]
            & holdout["t3_price_turn"]
            & holdout["t1_price_confirm"]
            & holdout["t1_volume_confirm"]
        ),
    }
    baseline_gain10 = holdout["d5_group"].ne("D5_LOSS").mean()
    baseline_gain20 = holdout["d5_group"].eq("D5_GAIN_GE_20").mean()
    records: list[dict[str, Any]] = []
    for stage, mask in masks.items():
        selected = holdout[mask.fillna(False)].copy()
        gain10 = selected["d5_group"].ne("D5_LOSS").mean() if len(selected) else np.nan
        gain20 = (
            selected["d5_group"].eq("D5_GAIN_GE_20").mean()
            if len(selected)
            else np.nan
        )
        returns = pd.to_numeric(selected["d5_adjusted_return_pct"], errors="coerce")
        records.append(
            {
                "holdout_start": holdout_start,
                "stage": stage,
                "selected_rows": int(len(selected)),
                "unique_stocks": int(selected["stock_id"].nunique()),
                "gain_ge10_rate": gain10,
                "gain_ge20_rate": gain20,
                "loss_rate": selected["d5_group"].eq("D5_LOSS").mean()
                if len(selected)
                else np.nan,
                "gain_ge10_lift_vs_baseline": gain10 / baseline_gain10
                if baseline_gain10
                else np.nan,
                "gain_ge20_lift_vs_baseline": gain20 / baseline_gain20
                if baseline_gain20
                else np.nan,
                "avg_d5_adjusted_return_pct": returns.mean(),
                "median_d5_adjusted_return_pct": returns.median(),
            }
        )
    return _round_numeric(pd.DataFrame(records))


def summarize_trajectories(rows: pd.DataFrame, *, scope: str) -> pd.DataFrame:
    features = [
        "t5_to_t1_return_pct",
        "t5_to_t1_k_change",
        "t5_to_t1_volume_ratio_change",
        "t5_to_t1_ma20_gap_change_pctpt",
    ]
    records: list[dict[str, Any]] = []
    for group_key, group in rows.groupby("d5_group", sort=False):
        for feature in features:
            values = pd.to_numeric(group[feature], errors="coerce").dropna()
            records.append(
                {
                    "scope": scope,
                    "d5_group": group_key,
                    "d5_group_order": GROUP_ORDER[group_key],
                    "feature": feature,
                    "rows": int(len(values)),
                    "mean": values.mean() if not values.empty else np.nan,
                    "median": values.median() if not values.empty else np.nan,
                }
            )
    return _round_numeric(pd.DataFrame(records))


def assert_no_lookahead(rows: pd.DataFrame) -> None:
    available = rows[rows["feature_date"].fillna("").astype(str).ne("")].copy()
    if available.empty:
        return
    feature_date = pd.to_datetime(available["feature_date"], errors="coerce")
    signal_date = pd.to_datetime(available["asof_date"], errors="coerce")
    if feature_date.isna().any() or (feature_date >= signal_date).any():
        raise AssertionError("lead snapshot used signal-day or future data")


def run_analysis(
    *,
    input_csv: Path,
    cooldown_csv: Path,
    sqlite_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    signals = pd.read_csv(input_csv, dtype={"stock_id": str})
    signals["stock_id"] = signals["stock_id"].astype(str).str.zfill(4)
    signals = signals[signals["d5_group"].isin(GROUP_ORDER)].copy()
    cooldown = pd.read_csv(cooldown_csv, dtype={"stock_id": str})
    cooldown_keys = set(
        cooldown["asof_date"].astype(str) + "|" + cooldown["stock_id"].astype(str).str.zfill(4)
    )
    signal_dates = pd.to_datetime(signals["asof_date"])
    history = load_adjusted_history(
        sqlite_path,
        stock_ids=sorted(signals["stock_id"].unique()),
        start_date=(signal_dates.min() - pd.Timedelta(days=500)).date().isoformat(),
        end_date=(signal_dates.max() - pd.Timedelta(days=1)).date().isoformat(),
    )
    snapshots = build_lead_snapshots(signals, history)
    event_keys = snapshots["asof_date"].astype(str) + "|" + snapshots["stock_id"].astype(str)
    snapshots["same_stock_cooldown"] = event_keys.isin(cooldown_keys)
    snapshots["corporate_action_event_in_horizon"] = _as_bool(
        snapshots["corporate_action_event_in_horizon"]
    )
    scopes = {
        "all_events": snapshots,
        "no_corporate_action": snapshots[~snapshots["corporate_action_event_in_horizon"]],
        "same_stock_cooldown": snapshots[snapshots["same_stock_cooldown"]],
        "no_corp_same_stock_cooldown": snapshots[
            (~snapshots["corporate_action_event_in_horizon"])
            & snapshots["same_stock_cooldown"]
        ],
    }
    group_stats = pd.concat(
        [build_group_stats(scope_rows, scope=scope) for scope, scope_rows in scopes.items()],
        ignore_index=True,
    )
    condition_shares = pd.concat(
        [
            build_condition_shares(scope_rows, scope=scope)
            for scope, scope_rows in scopes.items()
        ],
        ignore_index=True,
    )
    pairwise = pd.concat(
        [build_pairwise(scope_rows, scope=scope) for scope, scope_rows in scopes.items()],
        ignore_index=True,
    )
    trajectories = build_trajectories(snapshots)
    trajectory_keys = trajectories["asof_date"].astype(str) + "|" + trajectories["stock_id"].astype(str)
    trajectories["same_stock_cooldown"] = trajectory_keys.isin(cooldown_keys)
    action_keys = set(
        signals.loc[
            _as_bool(signals["corporate_action_event_in_horizon"]), ["asof_date", "stock_id"]
        ].astype(str).agg("|".join, axis=1)
    )
    trajectories["corporate_action_event_in_horizon"] = trajectory_keys.isin(action_keys)
    trajectory_scopes = {
        "all_events": trajectories,
        "no_corporate_action": trajectories[~trajectories["corporate_action_event_in_horizon"]],
        "same_stock_cooldown": trajectories[trajectories["same_stock_cooldown"]],
        "no_corp_same_stock_cooldown": trajectories[
            (~trajectories["corporate_action_event_in_horizon"])
            & trajectories["same_stock_cooldown"]
        ],
    }
    trajectory_stats = pd.concat(
        [
            summarize_trajectories(scope_rows, scope=scope)
            for scope, scope_rows in trajectory_scopes.items()
        ],
        ignore_index=True,
    )
    early_stage_rows = build_early_stage_rows(snapshots)
    early_stage_validation = evaluate_early_stage_rules(early_stage_rows)
    result = {
        "snapshots": snapshots,
        "group_stats": group_stats,
        "condition_shares": condition_shares,
        "pairwise": pairwise,
        "trajectories": trajectories,
        "trajectory_stats": trajectory_stats,
        "early_stage_rows": early_stage_rows,
        "early_stage_validation": early_stage_validation,
    }
    write_outputs(result, output_dir=output_dir)
    return result


def load_adjusted_history(
    sqlite_path: Path,
    *,
    stock_ids: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select date, stock_id, adj_open, adj_high, adj_low, adj_close, volume,
               adjustment_factor, factor_event_count, asof_date as adjusted_data_asof
        from tw_adjusted_ohlcv_daily
        where date between ? and ? and stock_id in ({placeholders})
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[start_date, end_date, *stock_ids],
            parse_dates=["date"],
        )


def write_outputs(result: dict[str, Any], *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "zhu_walkline_kd_d5_lead_snapshot_rows.csv": result["snapshots"],
        "zhu_walkline_kd_d5_lead_snapshot_group_stats.csv": result["group_stats"],
        "zhu_walkline_kd_d5_lead_snapshot_condition_shares.csv": result[
            "condition_shares"
        ],
        "zhu_walkline_kd_d5_lead_snapshot_pairwise.csv": result["pairwise"],
        "zhu_walkline_kd_d5_lead_trajectories.csv": result["trajectories"],
        "zhu_walkline_kd_d5_lead_trajectory_stats.csv": result["trajectory_stats"],
        "zhu_walkline_kd_d5_early_stage_rows.csv": result["early_stage_rows"],
        "zhu_walkline_kd_d5_early_stage_validation.csv": result[
            "early_stage_validation"
        ],
    }
    for name, frame in files.items():
        _clean_output(frame).to_csv(output_dir / name, index=False, encoding="utf-8-sig")
    summary = build_summary(result)
    (output_dir / "zhu_walkline_kd_d5_lead_snapshot_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_kd_d5_lead_snapshot_summary.md").write_text(
        render_markdown(result, summary),
        encoding="utf-8",
    )


def build_summary(result: dict[str, Any]) -> dict[str, Any]:
    snapshots = result["snapshots"]
    events = snapshots.drop_duplicates(["asof_date", "stock_id"])
    return {
        "purpose": "exact_t_minus_5_3_1_common_trait_research",
        "signal_start_date": str(events["asof_date"].min()),
        "signal_end_date": str(events["asof_date"].max()),
        "event_rows": int(len(events)),
        "snapshot_rows": int(len(snapshots)),
        "lead_offsets": list(LEAD_OFFSETS),
        "group_event_counts": {
            key: int(events["d5_group"].eq(key).sum()) for key in GROUP_ORDER
        },
        "price_basis": "adjusted OHLCV",
        "no_lookahead": "feature_date is strictly earlier than signal_date",
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "promotion_decision": "blocked_before_promotion_review",
    }


def render_markdown(result: dict[str, Any], summary: dict[str, Any]) -> str:
    stats = result["group_stats"]
    shares = result["condition_shares"]
    trajectory = result["trajectory_stats"]
    early_validation = result["early_stage_validation"]
    primary_stats = stats[stats["scope"].eq("all_events")]
    primary_shares = shares[shares["scope"].eq("all_events")]
    selected_numeric = [
        "daily_return_pct",
        "return_5d_pct",
        "return_20d_pct",
        "close_to_sma20_pct",
        "sma20_slope_5d_pct",
        "day_volume_ratio_20",
        "kd_k9",
        "kd_k_change_1d",
    ]
    selected_conditions = [
        "quiet_volume",
        "kd_k_rising",
        "close_above_sma20",
        "sma20_slope_positive",
        "expanded_volume",
        "strong_uptrend",
    ]
    lines = [
        "# KD D+5 訊號日前 T-5／T-3／T-1 共同特徵",
        "",
        "本報告為 shadow evaluator research，不是買進名單或交易指令。",
        "",
        f"- signal window: {summary['signal_start_date']} to {summary['signal_end_date']}",
        f"- events: {summary['event_rows']}; snapshots: {summary['snapshot_rows']}",
        "- T-N 定義：該股票訊號日前第 N 個實際交易日。",
        "- 價格基礎：調整後 OHLCV；所有 feature_date 嚴格早於 signal_date。",
        "",
        "## 數值中位數",
        "",
        "| lead | feature | loss | +10%~<20% | >=20% |",
        "|---|---|---:|---:|---:|",
    ]
    for offset in LEAD_OFFSETS:
        for feature in selected_numeric:
            subset = primary_stats[
                primary_stats["lead_offset"].eq(offset)
                & primary_stats["feature"].eq(feature)
            ].set_index("d5_group")
            lines.append(
                f"| T-{offset} | {FEATURE_LABELS[feature]} | "
                f"{_fmt(subset.get('median', pd.Series()).get('D5_LOSS'))} | "
                f"{_fmt(subset.get('median', pd.Series()).get('D5_GAIN_10_20'))} | "
                f"{_fmt(subset.get('median', pd.Series()).get('D5_GAIN_GE_20'))} |"
            )
    lines.extend(
        [
            "",
            "## 條件出現比例",
            "",
            "| lead | condition | loss | +10%~<20% | >=20% |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for offset in LEAD_OFFSETS:
        for condition in selected_conditions:
            subset = primary_shares[
                primary_shares["lead_offset"].eq(offset)
                & primary_shares["condition"].eq(condition)
            ].set_index("d5_group")
            lines.append(
                f"| T-{offset} | {CONDITION_LABELS[condition]} | "
                f"{_pct(subset.get('share', pd.Series()).get('D5_LOSS'))} | "
                f"{_pct(subset.get('share', pd.Series()).get('D5_GAIN_10_20'))} | "
                f"{_pct(subset.get('share', pd.Series()).get('D5_GAIN_GE_20'))} |"
            )
    primary_trajectory = trajectory[trajectory["scope"].eq("all_events")]
    lines.extend(
        [
            "",
            "## T-5 到 T-1 軌跡中位數",
            "",
            "| feature | loss | +10%~<20% | >=20% |",
            "|---|---:|---:|---:|",
        ]
    )
    for feature in [
        "t5_to_t1_return_pct",
        "t5_to_t1_k_change",
        "t5_to_t1_volume_ratio_change",
        "t5_to_t1_ma20_gap_change_pctpt",
    ]:
        subset = primary_trajectory[primary_trajectory["feature"].eq(feature)].set_index(
            "d5_group"
        )
        lines.append(
            f"| {feature} | {_fmt(subset.get('median', pd.Series()).get('D5_LOSS'))} | "
            f"{_fmt(subset.get('median', pd.Series()).get('D5_GAIN_10_20'))} | "
            f"{_fmt(subset.get('median', pd.Series()).get('D5_GAIN_GE_20'))} |"
        )
    robust_trajectory = trajectory[
        trajectory["scope"].eq("no_corp_same_stock_cooldown")
    ]
    lines.extend(
        [
            "",
            "## 排除公司行動與同股重疊後的 T-5 到 T-1 軌跡",
            "",
            "| feature | loss | +10%~<20% | >=20% |",
            "|---|---:|---:|---:|",
        ]
    )
    for feature in [
        "t5_to_t1_return_pct",
        "t5_to_t1_k_change",
        "t5_to_t1_volume_ratio_change",
        "t5_to_t1_ma20_gap_change_pctpt",
    ]:
        subset = robust_trajectory[
            robust_trajectory["feature"].eq(feature)
        ].set_index("d5_group")
        lines.append(
            f"| {feature} | {_fmt(subset.get('median', pd.Series()).get('D5_LOSS'))} | "
            f"{_fmt(subset.get('median', pd.Series()).get('D5_GAIN_10_20'))} | "
            f"{_fmt(subset.get('median', pd.Series()).get('D5_GAIN_GE_20'))} |"
        )
    lines.extend(
        [
            "",
            "## 共同軌跡判讀",
            "",
            "- T-5：兩個上漲組多數仍在月線下方、量比低於 0.75，屬縮量拉回而非攻擊。",
            "- T-3：日報酬轉正、K 值停止下滑或開始上彎，但多數仍未站回月線。",
            "- T-1：價格、月線乖離與量比同步回升，才形成較清楚的轉強確認。",
            "- 去除同股重疊後，KD 上升幅度不再穩定優於 loss；較穩健的是價格修復與量能加速。",
            "",
            "## Apr-Jun 分段條件驗證",
            "",
            "門檻沿用既有走圖定義：T-5量比<=0.75、T-3日報酬>0、T-1日報酬>0、T-1量比>=0.70。",
            "樣本排除公司行動並套同股5日cooldown；這是條件篩選證據，不是獨立未來OOS。",
            "",
            "| stage | rows | >=10% | >=20% | loss | avg D+5 | lift >=10% | lift >=20% |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in early_validation.itertuples(index=False):
        lines.append(
            f"| {row.stage} | {row.selected_rows} | {_pct(row.gain_ge10_rate)} | "
            f"{_pct(row.gain_ge20_rate)} | {_pct(row.loss_rate)} | "
            f"{_fmt(row.avg_d5_adjusted_return_pct)} | "
            f"{_fmt(row.gain_ge10_lift_vs_baseline)} | "
            f"{_fmt(row.gain_ge20_lift_vs_baseline)} |"
        )
    lines.extend(
        [
            "",
            "## 邊界",
            "",
            "- 這是描述性共同特徵，不是因果或可直接執行的規則。",
            "- 2026H1 單一期間仍有月份、類股與市場 regime 混淆。",
            "- 未定義進出場，因此未套用成本、滑價與成交限制。",
            "- mode=shadow_observation_only",
            "- formal_champion_changed=False",
            "- formal_trade_effect=False",
            "- promotion_decision=blocked_before_promotion_review",
        ]
    )
    return "\n".join(lines) + "\n"


def _condition_values(row: pd.Series) -> dict[str, bool]:
    return {
        "red_k": _number(row.get("open_to_close_pct")) > 0,
        "close_above_sma20": _number(row.get("close_to_sma20_pct")) > 0,
        "close_above_sma60": _number(row.get("close_to_sma60_pct")) > 0,
        "sma20_slope_positive": _number(row.get("sma20_slope_5d_pct")) > 0,
        "sma60_slope_positive": _number(row.get("sma60_slope_5d_pct")) > 0,
        "return_20d_positive": _number(row.get("return_20d_pct")) > 0,
        "kd_k_rising": _number(row.get("kd_k_change_1d")) > 0,
        "kd_above_d": _number(row.get("kd_k9")) > _number(row.get("kd_d9")),
        "kd_oversold": _number(row.get("kd_k9")) < 20,
        "quiet_volume": _number(row.get("day_volume_ratio_20")) <= 0.75,
        "expanded_volume": _number(row.get("day_volume_ratio_20")) >= 1.2,
        "close_high_in_bar": _number(row.get("close_location_in_bar")) >= 0.6,
        "strong_uptrend": (
            _number(row.get("close_to_sma20_pct")) > 0
            and _number(row.get("close_to_sma60_pct")) > 0
            and _number(row.get("sma20_slope_5d_pct")) > 0
            and _number(row.get("sma60_slope_5d_pct")) > 0
        ),
    }


def _early_stage(row: dict[str, Any]) -> str:
    if not bool(row["t5_quiet_setup"]):
        return "NO_EARLY_SETUP"
    if not bool(row["t3_price_turn"]):
        return "T5_SETUP"
    if not bool(row["t1_price_confirm"]):
        return "T3_EARLY_TURN"
    if not bool(row["t1_volume_confirm"]):
        return "T1_PRICE_CONFIRM"
    return "T1_PRICE_VOLUME_CONFIRM"


def _smoothed_kd(rsv: pd.Series) -> tuple[pd.Series, pd.Series]:
    previous_k = 50.0
    previous_d = 50.0
    k_values: list[float] = []
    d_values: list[float] = []
    for value in pd.to_numeric(rsv, errors="coerce").fillna(50.0):
        previous_k = (2.0 * previous_k + float(value)) / 3.0
        previous_d = (2.0 * previous_d + previous_k) / 3.0
        k_values.append(previous_k)
        d_values.append(previous_d)
    return pd.Series(k_values, index=rsv.index), pd.Series(d_values, index=rsv.index)


def _as_bool(values: pd.Series) -> pd.Series:
    return values.fillna(False).map(
        lambda value: value
        if isinstance(value, (bool, np.bool_))
        else str(value).strip().lower() in {"1", "true", "yes"}
    )


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _difference(start: Any, end: Any) -> float:
    first = _number(start)
    last = _number(end)
    return last - first if np.isfinite(first) and np.isfinite(last) else np.nan


def _pct_change(start: Any, end: Any) -> float:
    first = _number(start)
    last = _number(end)
    if not np.isfinite(first) or not np.isfinite(last) or first == 0:
        return np.nan
    return (last / first - 1.0) * 100.0


def _round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.select_dtypes(include=["float", "float64"]).columns:
        output[column] = output[column].round(8)
    return output


def _clean_output(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.select_dtypes(include=["object", "string"]).columns:
        output[column] = output[column].fillna("")
    return output.replace([np.inf, -np.inf], np.nan).fillna("")


def _fmt(value: Any) -> str:
    number = _number(value)
    return "" if not np.isfinite(number) else f"{number:.4f}"


def _pct(value: Any) -> str:
    number = _number(value)
    return "" if not np.isfinite(number) else f"{number * 100.0:.2f}%"


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default="reports/zhu_walkline_kd_d5_groups_2026_01_06/zhu_walkline_kd_d5_grouped_rows.csv",
    )
    parser.add_argument(
        "--cooldown-csv",
        default="reports/zhu_walkline_kd_d5_groups_2026_01_06/zhu_walkline_kd_d5_cooldown_rows.csv",
    )
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_kd_d5_lead_snapshots_2026_01_06",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = yaml.safe_load(_repo_path(args.config).read_text(encoding="utf-8"))
    result = run_analysis(
        input_csv=_repo_path(args.input_csv),
        cooldown_csv=_repo_path(args.cooldown_csv),
        sqlite_path=Path(config["data"]["sqlite_path"]),
        output_dir=_repo_path(args.output_dir),
    )
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"snapshot_rows={len(result['snapshots'])}")
    print(f"output_dir={_repo_path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
