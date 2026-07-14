"""Equal-weight shadow strength score for point-in-time pre-signal features."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd


SCORE_VERSION = "kd_d5_pre_signal_shadow_strength_v1"
REFERENCE_TASK = "D5_GAIN_GE10_VS_LOSS"


@dataclass(frozen=True)
class ShadowStrengthRule:
    """One discovery-period threshold used by the shadow strength score."""

    component: str
    feature: str
    source_date_column: str
    direction: Literal["HIGHER", "LOWER"]
    threshold: float
    points: int = 25
    reference_task: str = REFERENCE_TASK
    discovery_end: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


COMPONENT_SPECS = (
    ("main_force", "pre_main_force_net_lots_1d", "pre_main_force_source_date"),
    ("no_upper_tail", "pre5_upper_tail_count", "pre_price_source_date"),
    ("volume_ratio", "pre_day_volume_ratio_20", "pre_price_source_date"),
    (
        "margin_change",
        "pre_margin_balance_change_5d_pct",
        "pre_margin_available_date",
    ),
)


def build_shadow_strength_rules(
    reference: pd.DataFrame,
    *,
    task: str = REFERENCE_TASK,
) -> list[ShadowStrengthRule]:
    """Build four fixed, equal-weight rules from discovery-period references."""
    required = {"task", "feature", "direction", "threshold", "discovery_end"}
    missing = required - set(reference.columns)
    if missing:
        raise ValueError(f"reference missing required columns: {sorted(missing)}")
    rules: list[ShadowStrengthRule] = []
    for component, feature, source_date_column in COMPONENT_SPECS:
        matches = reference[
            reference["task"].eq(task) & reference["feature"].eq(feature)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one {task}/{feature} reference row, found {len(matches)}"
            )
        row = matches.iloc[0]
        direction = str(row["direction"])
        if direction not in {"HIGHER", "LOWER"}:
            raise ValueError(f"invalid direction for {feature}: {direction}")
        threshold = pd.to_numeric(pd.Series([row["threshold"]]), errors="coerce").iloc[0]
        if pd.isna(threshold) or not np.isfinite(float(threshold)):
            raise ValueError(f"invalid threshold for {feature}: {row['threshold']}")
        rules.append(
            ShadowStrengthRule(
                component=component,
                feature=feature,
                source_date_column=source_date_column,
                direction=direction,
                threshold=float(threshold),
                discovery_end=str(row["discovery_end"]),
            )
        )
    if sum(rule.points for rule in rules) != 100:
        raise AssertionError("shadow strength rules must sum to 100 points")
    return rules


def apply_shadow_strength_score(
    rows: pd.DataFrame,
    *,
    rules: list[ShadowStrengthRule],
) -> pd.DataFrame:
    """Apply four as-of rules without using any forward label columns."""
    if len(rules) != 4:
        raise ValueError(f"shadow strength requires exactly four rules, got {len(rules)}")
    output = rows.copy()
    required = {"asof_date", "stock_id"}
    required.update(rule.feature for rule in rules)
    required.update(rule.source_date_column for rule in rules)
    missing = required - set(output.columns)
    if missing:
        raise ValueError(f"rows missing shadow strength columns: {sorted(missing)}")

    signal_date = pd.to_datetime(output["asof_date"], errors="raise")
    pass_columns: list[str] = []
    available_columns: list[str] = []
    point_columns: list[str] = []
    for rule in rules:
        source_date = pd.to_datetime(output[rule.source_date_column], errors="coerce")
        violation = source_date.notna() & source_date.ge(signal_date)
        if violation.any():
            raise ValueError(
                f"shadow strength source is not pre-signal: "
                f"{rule.source_date_column} violations={int(violation.sum())}"
            )
        values = pd.to_numeric(output[rule.feature], errors="coerce")
        available = values.notna() & source_date.notna()
        passed = (
            values.ge(rule.threshold)
            if rule.direction == "HIGHER"
            else values.le(rule.threshold)
        )
        pass_column = f"shadow_strength_{rule.component}_pass"
        available_column = f"shadow_strength_{rule.component}_available"
        point_column = f"shadow_strength_{rule.component}_points"
        pass_values = passed.astype("boolean")
        pass_values.loc[~available] = pd.NA
        output[pass_column] = pass_values
        output[available_column] = available
        output[point_column] = np.where(
            available,
            np.where(passed, rule.points, 0),
            np.nan,
        )
        pass_columns.append(pass_column)
        available_columns.append(available_column)
        point_columns.append(point_column)

    output["shadow_strength_available_components"] = output[available_columns].sum(axis=1)
    output["shadow_strength_passed_components"] = (
        output[pass_columns].fillna(False).astype(bool).sum(axis=1)
    )
    complete = output["shadow_strength_available_components"].eq(len(rules))
    output["shadow_strength_complete"] = complete
    output["shadow_strength_score"] = output[point_columns].sum(axis=1, min_count=len(rules))
    output.loc[~complete, "shadow_strength_score"] = np.nan
    output["shadow_strength_tier"] = _strength_tier(
        output["shadow_strength_score"], complete=complete
    )
    output["shadow_strength_score_status"] = np.where(
        complete, "COMPLETE", "INSUFFICIENT_FEATURES"
    )
    output["shadow_strength_missing_components"] = output.apply(
        lambda row: "|".join(
            rule.component
            for rule in rules
            if not bool(row[f"shadow_strength_{rule.component}_available"])
        ),
        axis=1,
    )
    output["shadow_strength_passed_component_names"] = output.apply(
        lambda row: "|".join(
            rule.component
            for rule in rules
            if pd.notna(row[f"shadow_strength_{rule.component}_pass"])
            and bool(row[f"shadow_strength_{rule.component}_pass"])
        ),
        axis=1,
    )
    output["shadow_strength_feature_available_date"] = pd.concat(
        [pd.to_datetime(output[rule.source_date_column], errors="coerce") for rule in rules],
        axis=1,
    ).max(axis=1).dt.strftime("%Y-%m-%d")
    output["shadow_strength_rank_within_signal_date"] = output.groupby(
        "asof_date", sort=False
    )["shadow_strength_score"].rank(method="dense", ascending=False)
    output["shadow_strength_rank_pct_within_signal_date"] = output.groupby(
        "asof_date", sort=False
    )["shadow_strength_score"].rank(method="average", pct=True, ascending=True)
    output["shadow_strength_rankable_count"] = output.groupby(
        "asof_date", sort=False
    )["shadow_strength_score"].transform("count")
    output["shadow_strength_score_version"] = SCORE_VERSION
    output["shadow_strength_mode"] = "shadow_observation_only"
    output["shadow_strength_formal_trade_effect"] = False
    return output


def evaluate_shadow_strength_holdout(
    rows: pd.DataFrame,
    *,
    holdout_start: str,
) -> pd.DataFrame:
    """Evaluate exact and cumulative score buckets on a later holdout."""
    required = {
        "asof_date",
        "stock_id",
        "d5_group",
        "d5_adjusted_return_pct",
        "shadow_strength_complete",
        "shadow_strength_score",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"rows missing validation columns: {sorted(missing)}")
    frame = rows.copy()
    frame["asof_date"] = pd.to_datetime(frame["asof_date"], errors="raise")
    holdout = frame[frame["asof_date"] >= pd.Timestamp(holdout_start)].copy()
    complete = holdout[holdout["shadow_strength_complete"].astype(bool)].copy()
    if complete.empty:
        return pd.DataFrame()
    base_gain10 = _gain10_rate(complete)
    base_gain20 = _gain20_rate(complete)
    total_dates = int(holdout["asof_date"].nunique())
    records: list[dict[str, Any]] = []
    for score, selected in complete.groupby("shadow_strength_score", sort=True):
        records.append(
            _evaluation_record(
                selected,
                view="exact_score",
                score_threshold=float(score),
                holdout_rows=len(holdout),
                complete_rows=len(complete),
                total_dates=total_dates,
                base_gain10=base_gain10,
                base_gain20=base_gain20,
            )
        )
    for threshold in sorted(complete["shadow_strength_score"].dropna().unique()):
        selected = complete[complete["shadow_strength_score"].ge(threshold)]
        records.append(
            _evaluation_record(
                selected,
                view="cumulative_min_score",
                score_threshold=float(threshold),
                holdout_rows=len(holdout),
                complete_rows=len(complete),
                total_dates=total_dates,
                base_gain10=base_gain10,
                base_gain20=base_gain20,
            )
        )
    return pd.DataFrame(records).sort_values(["view", "score_threshold"]).reset_index(
        drop=True
    )


def strength_monotonicity(validation: pd.DataFrame, *, view: str) -> dict[str, bool]:
    """Check whether higher scores improve conditional holdout outcomes."""
    frame = validation[validation["view"].eq(view)].sort_values("score_threshold")
    gain10 = _nondecreasing(frame["d5_gain_ge10_rate"])
    gain20 = _nondecreasing(frame["d5_gain_ge20_rate"])
    loss = _nonincreasing(frame["d5_loss_rate"])
    return {
        "gain_ge10_nondecreasing": gain10,
        "gain_ge20_nondecreasing": gain20,
        "loss_nonincreasing": loss,
        "all_pass": gain10 and gain20 and loss,
    }


def rules_frame(rules: list[ShadowStrengthRule]) -> pd.DataFrame:
    """Return a machine-readable rule table."""
    return pd.DataFrame([rule.to_dict() for rule in rules])


def _evaluation_record(
    selected: pd.DataFrame,
    *,
    view: str,
    score_threshold: float,
    holdout_rows: int,
    complete_rows: int,
    total_dates: int,
    base_gain10: float,
    base_gain20: float,
) -> dict[str, Any]:
    gain10 = _gain10_rate(selected)
    gain20 = _gain20_rate(selected)
    selected_dates = int(selected["asof_date"].nunique())
    returns = pd.to_numeric(selected["d5_adjusted_return_pct"], errors="coerce")
    return {
        "view": view,
        "score_threshold": score_threshold,
        "holdout_rows": int(holdout_rows),
        "complete_feature_rows": int(complete_rows),
        "selected_rows": int(len(selected)),
        "unique_stocks": int(selected["stock_id"].nunique()),
        "total_signal_dates": total_dates,
        "selected_signal_dates": selected_dates,
        "empty_signal_dates": total_dates - selected_dates,
        "empty_signal_date_rate": _safe_divide(total_dates - selected_dates, total_dates),
        "selection_coverage_vs_complete": _safe_divide(len(selected), complete_rows),
        "d5_gain_ge10_rate": gain10,
        "d5_gain_ge20_rate": gain20,
        "d5_loss_rate": float(selected["d5_group"].eq("D5_LOSS").mean()),
        "avg_d5_adjusted_return_pct": returns.mean(),
        "median_d5_adjusted_return_pct": returns.median(),
        "gain_ge10_lift_vs_complete": _safe_ratio(gain10, base_gain10),
        "gain_ge20_lift_vs_complete": _safe_ratio(gain20, base_gain20),
    }


def _strength_tier(score: pd.Series, *, complete: pd.Series) -> pd.Series:
    tier = pd.Series("INSUFFICIENT_FEATURES", index=score.index, dtype="string")
    tier.loc[complete & score.le(25)] = "SHADOW_STRENGTH_0_1_OF_4"
    tier.loc[complete & score.eq(50)] = "SHADOW_STRENGTH_2_OF_4"
    tier.loc[complete & score.eq(75)] = "SHADOW_STRENGTH_3_OF_4"
    tier.loc[complete & score.eq(100)] = "SHADOW_STRENGTH_4_OF_4"
    return tier


def _gain10_rate(rows: pd.DataFrame) -> float:
    return float(rows["d5_group"].isin({"D5_GAIN_10_20", "D5_GAIN_GE_20"}).mean())


def _gain20_rate(rows: pd.DataFrame) -> float:
    return float(rows["d5_group"].eq("D5_GAIN_GE_20").mean())


def _nondecreasing(values: pd.Series) -> bool:
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy()
    return bool(len(numeric) > 0 and np.all(np.diff(numeric) >= -1e-12))


def _nonincreasing(values: pd.Series) -> bool:
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy()
    return bool(len(numeric) > 0 and np.all(np.diff(numeric) <= 1e-12))


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else np.nan


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator
