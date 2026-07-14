"""Point-in-time D-10 through D trajectories for shadow timing research."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Iterable

import numpy as np
import pandas as pd


TRAJECTORY_LEADS = tuple(range(10, -1, -1))
TECHNICAL_COLUMNS = (
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "daily_return_pct",
    "return_5d_pct",
    "return_20d_pct",
    "close_to_sma20_pct",
    "sma20_slope_5d_pct",
    "day_volume_ratio_20",
    "close_location_in_bar",
    "range_pos_20",
    "open_to_close_pct",
    "kd_k9",
    "kd_d9",
    "kd_spread",
    "kd_k_change_1d",
)


@dataclass(frozen=True)
class EarlyTrajectoryRule:
    """One bounded, interpretable early-turn observation rule."""

    max_k: float
    min_k_change_1d: float
    min_daily_return_pct: float
    max_volume_ratio_20: float
    max_close_to_sma20_pct: float
    max_distance_from_trailing_5d_low_pct: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def build_event_trajectory(
    events: pd.DataFrame,
    feature_history: pd.DataFrame,
    *,
    maximum_lead_days: int = 10,
) -> pd.DataFrame:
    """Build exact stock-trading-day observations from D-10 through D."""
    event_required = {
        "asof_date",
        "stock_id",
        "stock_name",
        "d5_adjusted_return_pct",
    }
    history_required = {"date", "stock_id", *TECHNICAL_COLUMNS}
    missing_events = event_required - set(events.columns)
    missing_history = history_required - set(feature_history.columns)
    if missing_events:
        raise ValueError(f"events missing trajectory columns: {sorted(missing_events)}")
    if missing_history:
        raise ValueError(f"history missing trajectory columns: {sorted(missing_history)}")

    event_rows = events.copy()
    event_rows["asof_date"] = pd.to_datetime(event_rows["asof_date"], errors="raise")
    event_rows["stock_id"] = event_rows["stock_id"].astype(str).str.zfill(4)
    history = feature_history.copy()
    history["date"] = pd.to_datetime(history["date"], errors="raise")
    history["stock_id"] = history["stock_id"].astype(str).str.zfill(4)
    history = history.sort_values(["stock_id", "date"])
    groups = {
        stock_id: group.reset_index(drop=True)
        for stock_id, group in history.groupby("stock_id", sort=False)
    }

    records: list[dict[str, Any]] = []
    missing_keys: list[str] = []
    for event in event_rows.itertuples(index=False):
        stock_id = str(event.stock_id)
        signal_date = pd.Timestamp(event.asof_date)
        stock_history = groups.get(stock_id)
        if stock_history is None:
            missing_keys.append(f"{signal_date.date()}|{stock_id}|no_history")
            continue
        matches = stock_history.index[stock_history["date"].eq(signal_date)]
        if len(matches) != 1:
            missing_keys.append(f"{signal_date.date()}|{stock_id}|signal_row={len(matches)}")
            continue
        signal_index = int(matches[0])
        if signal_index < maximum_lead_days:
            missing_keys.append(f"{signal_date.date()}|{stock_id}|short_history")
            continue
        signal_row = stock_history.iloc[signal_index]
        base_row = stock_history.iloc[signal_index - maximum_lead_days]
        for lead_days in range(maximum_lead_days, -1, -1):
            row_index = signal_index - lead_days
            observation = stock_history.iloc[row_index]
            trailing = stock_history.iloc[max(0, row_index - 4) : row_index + 1]
            trailing_low = pd.to_numeric(trailing["adj_low"], errors="coerce").min()
            record = {
                "signal_date": signal_date.strftime("%Y-%m-%d"),
                "observation_date": pd.Timestamp(observation["date"]).strftime("%Y-%m-%d"),
                "stock_id": stock_id,
                "stock_name": str(event.stock_name),
                "lead_days": int(lead_days),
                "relative_day": f"D-{lead_days}" if lead_days else "D",
                "d5_adjusted_return_pct": float(event.d5_adjusted_return_pct),
                "return_from_d10_pct": _pct_change(
                    base_row["adj_close"], observation["adj_close"]
                ),
                "evaluator_return_observation_to_signal_pct": _pct_change(
                    observation["adj_close"], signal_row["adj_close"]
                ),
                "distance_from_trailing_5d_low_pct": _pct_change(
                    trailing_low, observation["adj_close"]
                ),
            }
            for column in TECHNICAL_COLUMNS:
                record[column] = observation[column]
            records.append(record)
    if missing_keys:
        sample = ", ".join(missing_keys[:5])
        raise ValueError(
            f"could not build complete D-{maximum_lead_days} trajectory for "
            f"{len(missing_keys)} events; sample={sample}"
        )
    output = pd.DataFrame(records)
    assert_trajectory_point_in_time(output)
    expected_rows = len(event_rows) * (maximum_lead_days + 1)
    if len(output) != expected_rows:
        raise AssertionError(f"trajectory rows {len(output)} != expected {expected_rows}")
    return output


def assert_trajectory_point_in_time(rows: pd.DataFrame) -> None:
    """Ensure technical observations never occur after their signal date."""
    observation = pd.to_datetime(rows["observation_date"], errors="raise")
    signal = pd.to_datetime(rows["signal_date"], errors="raise")
    if observation.gt(signal).any():
        raise AssertionError("trajectory contains post-signal technical observations")
    d_rows = rows[rows["lead_days"].eq(0)]
    if not pd.to_datetime(d_rows["observation_date"]).eq(
        pd.to_datetime(d_rows["signal_date"])
    ).all():
        raise AssertionError("D trajectory rows must equal the signal date")


def generate_trajectory_rules(
    search_grid: dict[str, list[float]],
) -> Iterable[EarlyTrajectoryRule]:
    """Yield the Cartesian product of the bounded timing grid."""
    names = (
        "max_k",
        "min_k_change_1d",
        "min_daily_return_pct",
        "max_volume_ratio_20",
        "max_close_to_sma20_pct",
        "max_distance_from_trailing_5d_low_pct",
    )
    for values in product(*(search_grid[name] for name in names)):
        yield EarlyTrajectoryRule(**dict(zip(names, map(float, values), strict=True)))


def trajectory_rule_mask(
    rows: pd.DataFrame,
    rule: EarlyTrajectoryRule,
    *,
    minimum_lead_days: int = 2,
    maximum_lead_days: int = 10,
) -> pd.Series:
    """Apply an early rule without reading outcome or future trajectory fields."""
    mask = rows["lead_days"].between(minimum_lead_days, maximum_lead_days)
    mask &= pd.to_numeric(rows["kd_k9"], errors="coerce").le(rule.max_k)
    mask &= pd.to_numeric(rows["kd_k_change_1d"], errors="coerce").ge(
        rule.min_k_change_1d
    )
    mask &= pd.to_numeric(rows["daily_return_pct"], errors="coerce").ge(
        rule.min_daily_return_pct
    )
    mask &= pd.to_numeric(rows["day_volume_ratio_20"], errors="coerce").le(
        rule.max_volume_ratio_20
    )
    mask &= pd.to_numeric(rows["close_to_sma20_pct"], errors="coerce").le(
        rule.max_close_to_sma20_pct
    )
    mask &= pd.to_numeric(
        rows["distance_from_trailing_5d_low_pct"], errors="coerce"
    ).le(rule.max_distance_from_trailing_5d_low_pct)
    return mask.fillna(False)


def earliest_alert_rows(rows: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Keep the earliest chronological alert in each event trajectory."""
    selected = rows[mask].copy()
    if selected.empty:
        return selected
    return (
        selected.sort_values(
            ["signal_date", "stock_id", "lead_days"],
            ascending=[True, True, False],
        )
        .drop_duplicates(["signal_date", "stock_id"], keep="first")
        .reset_index(drop=True)
    )


def build_t1_baseline_alerts(rows: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the prespecified T-5/T-3/T-1 confirmation baseline."""
    required_leads = {5, 3, 1}
    records: list[pd.Series] = []
    for _key, group in rows.groupby(["signal_date", "stock_id"], sort=False):
        indexed = group.set_index("lead_days")
        if not required_leads.issubset(indexed.index):
            continue
        t5 = indexed.loc[5]
        t3 = indexed.loc[3]
        t1 = indexed.loc[1]
        passes = (
            _number(t5["day_volume_ratio_20"]) <= 0.75
            and _number(t3["daily_return_pct"]) > 0.0
            and _number(t1["daily_return_pct"]) > 0.0
            and _number(t1["day_volume_ratio_20"]) >= 0.70
        )
        if passes:
            t1 = t1.copy()
            t1["lead_days"] = 1
            records.append(t1)
    return pd.DataFrame(records).reset_index(drop=True) if records else rows.iloc[0:0].copy()


def evaluate_event_alerts(
    event_rows: pd.DataFrame,
    alerts: pd.DataFrame,
    *,
    split: str,
) -> dict[str, Any]:
    """Evaluate one alert rule over unique events in a temporal split."""
    events = event_rows[event_rows["split"].eq(split)].copy()
    alert_keys = set(
        alerts[["signal_date", "stock_id"]].astype(str).agg("|".join, axis=1)
    )
    keys = events[["signal_date", "stock_id"]].astype(str).agg("|".join, axis=1)
    predicted = keys.isin(alert_keys)
    actual = events["target_gain_ge10"].astype(bool)
    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())
    tn = int((~predicted & ~actual).sum())
    selected = events[predicted].merge(
        alerts,
        on=["signal_date", "stock_id"],
        how="left",
        suffixes=("", "_alert"),
        validate="one_to_one",
    )
    precision = _divide(tp, tp + fp)
    recall = _divide(tp, tp + fn)
    specificity = _divide(tn, tn + fp)
    base_rate = float(actual.mean()) if len(events) else 0.0
    selected_months = int(
        pd.to_datetime(selected["signal_date"], errors="coerce")
        .dt.to_period("M")
        .nunique()
    )
    total_months = int(
        pd.to_datetime(events["signal_date"], errors="coerce")
        .dt.to_period("M")
        .nunique()
    )
    returns = pd.to_numeric(selected["d5_adjusted_return_pct"], errors="coerce")
    alert_to_signal = pd.to_numeric(
        selected["evaluator_return_observation_to_signal_pct"], errors="coerce"
    )
    alert_to_d5 = (
        (1.0 + alert_to_signal / 100.0) * (1.0 + returns / 100.0) - 1.0
    ) * 100.0
    return {
        "split": split,
        "split_rows": int(len(events)),
        "selected_rows": int(len(selected)),
        "unique_stocks": int(selected["stock_id"].nunique()),
        "selected_months": selected_months,
        "total_months": total_months,
        "empty_months": total_months - selected_months,
        "coverage": _divide(len(selected), len(events)),
        "precision_gain_ge10": precision,
        "recall_gain_ge10": recall,
        "f1_gain_ge10": _divide(2 * precision * recall, precision + recall),
        "specificity_gain_ge10": specificity,
        "balanced_accuracy_gain_ge10": (recall + specificity) / 2.0,
        "precision_lift_vs_all": _divide(precision, base_rate),
        "gain_ge20_rate": float(returns.ge(20).mean()) if len(selected) else 0.0,
        "loss_rate": float(returns.lt(0).mean()) if len(selected) else 0.0,
        "avg_d5_adjusted_return_pct": float(returns.mean()) if len(selected) else 0.0,
        "median_d5_adjusted_return_pct": float(returns.median())
        if len(selected)
        else 0.0,
        "gain_ge10_from_alert_to_d5_rate": float(alert_to_d5.ge(10).mean())
        if len(selected)
        else 0.0,
        "gain_ge20_from_alert_to_d5_rate": float(alert_to_d5.ge(20).mean())
        if len(selected)
        else 0.0,
        "loss_from_alert_to_d5_rate": float(alert_to_d5.lt(0).mean())
        if len(selected)
        else 0.0,
        "avg_alert_to_d5_adjusted_return_pct": float(alert_to_d5.mean())
        if len(selected)
        else 0.0,
        "median_alert_to_d5_adjusted_return_pct": float(alert_to_d5.median())
        if len(selected)
        else 0.0,
        "mean_lead_days": float(selected["lead_days"].mean()) if len(selected) else 0.0,
        "median_lead_days": float(selected["lead_days"].median()) if len(selected) else 0.0,
        "median_alert_to_signal_return_pct": float(
            selected["evaluator_return_observation_to_signal_pct"].median()
        )
        if len(selected)
        else 0.0,
        "median_distance_from_trailing_5d_low_pct": float(
            selected["distance_from_trailing_5d_low_pct"].median()
        )
        if len(selected)
        else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def event_frame_from_trajectory(
    rows: pd.DataFrame,
    *,
    target_return_pct: float,
    large_gain_return_pct: float,
) -> pd.DataFrame:
    """Return one target row per event; outcomes remain evaluator-only."""
    optional = [
        column
        for column in ("d5_close_date", "d5_adj_close", "signal_adj_close")
        if column in rows
    ]
    events = rows[rows["lead_days"].eq(0)][
        [
            "signal_date",
            "stock_id",
            "stock_name",
            "d5_adjusted_return_pct",
            "split",
            *optional,
        ]
    ].copy()
    events["target_gain_ge10"] = events["d5_adjusted_return_pct"].ge(
        target_return_pct
    )
    events["target_gain_ge20"] = events["d5_adjusted_return_pct"].ge(
        large_gain_return_pct
    )
    events["target_loss"] = events["d5_adjusted_return_pct"].lt(0)
    return events.reset_index(drop=True)


def build_relative_day_profile(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize winner/non-winner trajectories by split and relative day."""
    records: list[dict[str, Any]] = []
    for (split, lead_days), group in rows.groupby(["split", "lead_days"], sort=False):
        for outcome, selected in group.groupby("target_gain_ge10", sort=False):
            score = pd.to_numeric(selected.get("shadow_strength_score"), errors="coerce")
            records.append(
                {
                    "split": split,
                    "lead_days": int(lead_days),
                    "relative_day": f"D-{lead_days}" if lead_days else "D",
                    "target_gain_ge10": bool(outcome),
                    "rows": int(len(selected)),
                    "complete_strength_rate": float(
                        selected.get(
                            "shadow_strength_complete",
                            pd.Series(False, index=selected.index),
                        )
                        .fillna(False)
                        .astype(bool)
                        .mean()
                    ),
                    "mean_shadow_strength_score": float(score.mean()),
                    "median_shadow_strength_score": float(score.median()),
                    "median_daily_return_pct": float(selected["daily_return_pct"].median()),
                    "median_return_from_d10_pct": float(
                        selected["return_from_d10_pct"].median()
                    ),
                    "median_close_to_sma20_pct": float(
                        selected["close_to_sma20_pct"].median()
                    ),
                    "median_volume_ratio_20": float(
                        selected["day_volume_ratio_20"].median()
                    ),
                    "median_k": float(selected["kd_k9"].median()),
                    "median_k_change_1d": float(
                        selected["kd_k_change_1d"].median()
                    ),
                }
            )
    return pd.DataFrame(records).sort_values(
        ["split", "lead_days", "target_gain_ge10"],
        ascending=[True, False, True],
    )


def _pct_change(start: Any, end: Any) -> float:
    start_number = _number(start)
    end_number = _number(end)
    if not np.isfinite(start_number) or not np.isfinite(end_number) or start_number == 0:
        return np.nan
    return (end_number / start_number - 1.0) * 100.0


def _number(value: Any) -> float:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(number) if pd.notna(number) else np.nan


def _divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0
