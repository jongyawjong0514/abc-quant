"""Causal D-10 factor-frontier helpers for full-market shadow research.

The helpers in this module are intentionally independent from the Zhu signal
implementation.  They operate on already point-in-time feature rows and keep
all label-driven choices inside a caller-supplied discovery split.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


SPLIT_ORDER = ("DISCOVERY", "VALIDATION", "CALIBRATION", "HOLDOUT")


@dataclass(frozen=True)
class D10FixedRule:
    """Previously frozen six-condition early-start rule."""

    max_k: float
    min_k_change_1d: float
    min_daily_return_pct: float
    max_volume_ratio_20: float
    max_close_to_sma20_pct: float
    max_distance_from_trailing_5d_low_pct: float


def prespecified_t1_mask(
    rows: pd.DataFrame,
    *,
    max_t5_volume_ratio_20: float,
    min_t3_daily_return_pct: float,
    min_t1_daily_return_pct: float,
    min_t1_volume_ratio_20: float,
    date_column: str = "observation_date",
    volume_ratio_column: str = "volume_ratio_20",
    return_column: str = "return_1d_pct",
) -> pd.Series:
    """Apply the frozen T-5/T-3/T-1 price-volume chain causally.

    The input row is the T-1 observation.  T-5 and T-3 therefore correspond
    to four and two stock trading rows before it.  No outcome column is read.
    """

    required = {"stock_id", date_column, volume_ratio_column, return_column}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"T1 rows missing columns: {sorted(missing)}")
    ordered = rows.sort_values(["stock_id", date_column]).copy()
    grouped = ordered.groupby("stock_id", sort=False, group_keys=False)
    t5_volume = grouped[volume_ratio_column].shift(4)
    t3_return = grouped[return_column].shift(2)
    current_return = pd.to_numeric(ordered[return_column], errors="coerce")
    current_volume = pd.to_numeric(ordered[volume_ratio_column], errors="coerce")
    mask = (
        pd.to_numeric(t5_volume, errors="coerce").le(max_t5_volume_ratio_20)
        & pd.to_numeric(t3_return, errors="coerce").gt(min_t3_daily_return_pct)
        & current_return.gt(min_t1_daily_return_pct)
        & current_volume.ge(min_t1_volume_ratio_20)
    )
    return mask.fillna(False).reindex(rows.index)


def d10_fixed_rule_mask(rows: pd.DataFrame, rule: D10FixedRule) -> pd.Series:
    """Apply the previously frozen six-condition negative-control rule."""

    required = {
        "kd_k9",
        "kd_k_change_1d",
        "return_1d_pct",
        "volume_ratio_20",
        "close_to_ma20_pct",
        "distance_from_trailing_5d_low_pct",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"D10 fixed rows missing columns: {sorted(missing)}")
    mask = pd.to_numeric(rows["kd_k9"], errors="coerce").le(rule.max_k)
    mask &= pd.to_numeric(rows["kd_k_change_1d"], errors="coerce").ge(
        rule.min_k_change_1d
    )
    mask &= pd.to_numeric(rows["return_1d_pct"], errors="coerce").ge(
        rule.min_daily_return_pct
    )
    mask &= pd.to_numeric(rows["volume_ratio_20"], errors="coerce").le(
        rule.max_volume_ratio_20
    )
    mask &= pd.to_numeric(rows["close_to_ma20_pct"], errors="coerce").le(
        rule.max_close_to_sma20_pct
    )
    mask &= pd.to_numeric(
        rows["distance_from_trailing_5d_low_pct"], errors="coerce"
    ).le(rule.max_distance_from_trailing_5d_low_pct)
    return mask.fillna(False)


def assign_label_maturity_purged_splits(
    rows: pd.DataFrame,
    *,
    windows: Mapping[str, tuple[str, str]],
    date_column: str = "asof_date",
    label_date_column: str = "exit_date",
) -> tuple[pd.Series, pd.DataFrame]:
    """Assign chronological splits after the prior split's labels mature."""

    if set(windows) != set(SPLIT_ORDER):
        raise ValueError(f"windows must contain exactly {SPLIT_ORDER}")
    dates = pd.to_datetime(rows[date_column], errors="raise")
    label_dates = pd.to_datetime(rows[label_date_column], errors="coerce")
    assigned = pd.Series("PURGED", index=rows.index, dtype="object")
    prior_freeze = pd.NaT
    audit: list[dict[str, Any]] = []
    for split in SPLIT_ORDER:
        start_text, end_text = windows[split]
        raw = dates.between(pd.Timestamp(start_text), pd.Timestamp(end_text))
        keep = raw.copy()
        if pd.notna(prior_freeze):
            keep &= dates.gt(prior_freeze)
        assigned.loc[keep] = split
        current_label_dates = label_dates.loc[keep].dropna()
        current_freeze = (
            current_label_dates.max() if not current_label_dates.empty else pd.NaT
        )
        effective_dates = dates.loc[keep]
        audit.append(
            {
                "split": split,
                "configured_start": start_text,
                "configured_end": end_text,
                "prior_label_freeze_date": _date_text(prior_freeze),
                "effective_start": _date_text(effective_dates.min()),
                "effective_end": _date_text(effective_dates.max()),
                "raw_rows": int(raw.sum()),
                "kept_rows": int(keep.sum()),
                "purged_rows": int(raw.sum() - keep.sum()),
                "label_freeze_date": _date_text(current_freeze),
            }
        )
        prior_freeze = current_freeze
    return assigned, pd.DataFrame(audit)


def build_factor_permutation_frontier(
    discovery: pd.DataFrame,
    *,
    feature_columns: Iterable[str],
    target_column: str,
    return_column: str,
    date_column: str,
    repetitions: int,
    random_seed: int,
    minimum_coverage: float,
    lower_quantile: float = 0.25,
    upper_quantile: float = 0.75,
) -> pd.DataFrame:
    """Rank factors with within-date permutations and max-T protection.

    Missing values are median-imputed solely for the standardized effect test.
    Threshold selection itself excludes missing values and uses only discovery
    quantiles.  Labels are permuted within each trading date so market-regime
    hit rates and cross-sectional dependence remain represented in the null.
    """

    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    if not 0.0 < lower_quantile < upper_quantile < 1.0:
        raise ValueError("quantiles must satisfy 0 < lower < upper < 1")
    target = pd.to_numeric(discovery[target_column], errors="coerce")
    valid_target = target.isin([0, 1])
    rows = discovery.loc[valid_target].copy()
    y = target.loc[valid_target].astype(int).to_numpy(dtype=float)
    if y.sum() == 0 or y.sum() == len(y):
        raise ValueError("discovery target must contain both classes")

    kept_features: list[str] = []
    original_values: list[pd.Series] = []
    standardized: list[np.ndarray] = []
    coverages: list[float] = []
    medians: list[float] = []
    stds: list[float] = []
    for feature in feature_columns:
        if feature not in rows:
            continue
        values = pd.to_numeric(rows[feature], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        coverage = float(values.notna().mean())
        if coverage < minimum_coverage:
            continue
        median = float(values.median())
        filled = values.fillna(median).to_numpy(dtype=float)
        std = float(np.std(filled))
        if not np.isfinite(std) or std <= 1e-12:
            continue
        kept_features.append(feature)
        original_values.append(values)
        standardized.append((filled - float(np.mean(filled))) / std)
        coverages.append(coverage)
        medians.append(median)
        stds.append(std)
    if not kept_features:
        return pd.DataFrame()

    matrix = np.column_stack(standardized)
    observed = _class_mean_difference(matrix, y)
    rng = np.random.default_rng(random_seed)
    block_indices = [
        group.index.to_numpy(dtype=int)
        for _, group in rows.reset_index(drop=True).groupby(date_column, sort=False)
    ]
    exceed = np.zeros(len(kept_features), dtype=int)
    max_exceed = np.zeros(len(kept_features), dtype=int)
    absolute_observed = np.abs(observed)
    for _ in range(repetitions):
        permuted = y.copy()
        for indices in block_indices:
            permuted[indices] = rng.permutation(permuted[indices])
        null_effect = np.abs(_class_mean_difference(matrix, permuted))
        exceed += null_effect >= absolute_observed - 1e-15
        max_null = float(np.nanmax(null_effect))
        max_exceed += max_null >= absolute_observed - 1e-15
    p_values = (exceed + 1.0) / (repetitions + 1.0)
    max_t_p_values = (max_exceed + 1.0) / (repetitions + 1.0)
    q_values = benjamini_hochberg(p_values)

    returns = pd.to_numeric(rows[return_column], errors="coerce")
    records: list[dict[str, Any]] = []
    for index, feature in enumerate(kept_features):
        values = original_values[index]
        direction = ">=" if observed[index] >= 0 else "<="
        quantile = upper_quantile if direction == ">=" else lower_quantile
        threshold = float(values.dropna().quantile(quantile))
        selected = values.ge(threshold) if direction == ">=" else values.le(threshold)
        selected &= values.notna()
        selected_target = pd.Series(y, index=rows.index).loc[selected]
        selected_returns = returns.loc[selected]
        records.append(
            {
                "feature": feature,
                "direction": direction,
                "threshold": threshold,
                "threshold_quantile": quantile,
                "coverage": coverages[index],
                "discovery_median": medians[index],
                "discovery_std": stds[index],
                "standardized_effect": float(observed[index]),
                "absolute_standardized_effect": float(absolute_observed[index]),
                "permutation_p_value": float(p_values[index]),
                "bh_q_value": float(q_values[index]),
                "max_t_fwer_p_value": float(max_t_p_values[index]),
                "discovery_selected_rows": int(selected.sum()),
                "discovery_selected_rate": float(selected.mean()),
                "discovery_gain_ge_target_rate": _mean(selected_target),
                "discovery_loss_rate": float(selected_returns.lt(0).mean())
                if len(selected_returns)
                else np.nan,
                "discovery_mean_return_pct": _mean(selected_returns),
                "discovery_median_return_pct": _median(selected_returns),
            }
        )
    return pd.DataFrame(records).sort_values(
        ["max_t_fwer_p_value", "absolute_standardized_effect", "feature"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def evaluate_frozen_factor_thresholds(
    rows: pd.DataFrame,
    frontier: pd.DataFrame,
    *,
    split_column: str,
    target_column: str,
    return_column: str,
) -> pd.DataFrame:
    """Apply discovery-frozen factor directions and thresholds to every split."""

    records: list[dict[str, Any]] = []
    for factor in frontier.itertuples(index=False):
        feature = str(factor.feature)
        if feature not in rows:
            continue
        values = pd.to_numeric(rows[feature], errors="coerce")
        selected = (
            values.ge(float(factor.threshold))
            if factor.direction == ">="
            else values.le(float(factor.threshold))
        )
        selected &= values.notna()
        for split, group in rows.groupby(split_column, sort=False):
            mask = selected.loc[group.index]
            target = pd.to_numeric(group[target_column], errors="coerce")
            returns = pd.to_numeric(group[return_column], errors="coerce")
            chosen_target = target.loc[mask]
            chosen_returns = returns.loc[mask]
            records.append(
                {
                    "feature": feature,
                    "direction": factor.direction,
                    "threshold": float(factor.threshold),
                    "split": split,
                    "rows": int(len(group)),
                    "selected_rows": int(mask.sum()),
                    "selected_rate": float(mask.mean()) if len(mask) else 0.0,
                    "base_gain_rate": _mean(target),
                    "selected_gain_rate": _mean(chosen_target),
                    "precision_lift_vs_split": _safe_divide(
                        _mean(chosen_target), _mean(target)
                    ),
                    "selected_loss_rate": float(chosen_returns.lt(0).mean())
                    if len(chosen_returns)
                    else np.nan,
                    "selected_mean_return_pct": _mean(chosen_returns),
                    "selected_median_return_pct": _median(chosen_returns),
                }
            )
    return pd.DataFrame(records)


def build_fixed_volume_threshold_table(
    rows: pd.DataFrame,
    *,
    feature_columns: Iterable[str],
    thresholds: Iterable[float],
    split_column: str,
    target_column: str,
    return_column: str,
) -> pd.DataFrame:
    """Evaluate predeclared volume thresholds without selecting a winner."""

    records: list[dict[str, Any]] = []
    for feature in feature_columns:
        if feature not in rows:
            continue
        values = pd.to_numeric(rows[feature], errors="coerce")
        for threshold in thresholds:
            for direction in ("<=", ">="):
                selected = values.le(threshold) if direction == "<=" else values.ge(threshold)
                selected &= values.notna()
                for split, group in rows.groupby(split_column, sort=False):
                    mask = selected.loc[group.index]
                    target = pd.to_numeric(group[target_column], errors="coerce")
                    returns = pd.to_numeric(group[return_column], errors="coerce")
                    chosen_target = target.loc[mask]
                    chosen_returns = returns.loc[mask]
                    records.append(
                        {
                            "feature": feature,
                            "direction": direction,
                            "threshold": float(threshold),
                            "split": split,
                            "rows": int(len(group)),
                            "selected_rows": int(mask.sum()),
                            "selected_rate": float(mask.mean()) if len(mask) else 0.0,
                            "base_gain_rate": _mean(target),
                            "selected_gain_rate": _mean(chosen_target),
                            "precision_lift_vs_split": _safe_divide(
                                _mean(chosen_target), _mean(target)
                            ),
                            "selected_loss_rate": float(chosen_returns.lt(0).mean())
                            if len(chosen_returns)
                            else np.nan,
                            "selected_mean_return_pct": _mean(chosen_returns),
                            "selected_median_return_pct": _median(chosen_returns),
                        }
                    )
    return pd.DataFrame(records)


def build_event_factor_profile(
    rows: pd.DataFrame,
    *,
    feature_columns: Iterable[str],
    return_column: str = "d5_adjusted_return_pct",
) -> pd.DataFrame:
    """Create long D-10 through D summaries for the three requested outcomes."""

    frame = rows.copy()
    returns = pd.to_numeric(frame[return_column], errors="coerce")
    frame["outcome_group"] = np.select(
        [returns.lt(0), returns.ge(10) & returns.lt(20), returns.ge(20)],
        ["D5_LOSS", "D5_GAIN_10_20", "D5_GAIN_GE20"],
        default="UNGROUPED_0_10",
    )
    frame = frame[frame["outcome_group"].ne("UNGROUPED_0_10")]
    records: list[dict[str, Any]] = []
    for feature in feature_columns:
        if feature not in frame:
            continue
        values = pd.to_numeric(frame[feature], errors="coerce")
        work = frame[["lead_days", "relative_day", "outcome_group"]].copy()
        work["value"] = values
        for keys, group in work.groupby(
            ["lead_days", "relative_day", "outcome_group"], sort=True
        ):
            numeric = group["value"].dropna()
            records.append(
                {
                    "lead_days": int(keys[0]),
                    "relative_day": keys[1],
                    "outcome_group": keys[2],
                    "feature": feature,
                    "rows": int(len(group)),
                    "available_rows": int(len(numeric)),
                    "coverage": _safe_divide(len(numeric), len(group)),
                    "mean": _mean(numeric),
                    "median": _median(numeric),
                    "q25": float(numeric.quantile(0.25)) if len(numeric) else np.nan,
                    "q75": float(numeric.quantile(0.75)) if len(numeric) else np.nan,
                }
            )
    return pd.DataFrame(records)


def benjamini_hochberg(p_values: Iterable[float]) -> np.ndarray:
    """Return monotone Benjamini-Hochberg adjusted q-values."""

    values = np.asarray(list(p_values), dtype=float)
    if values.size == 0:
        return values
    order = np.argsort(values)
    ranked = values[order]
    adjusted = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    output = np.empty_like(adjusted)
    output[order] = np.clip(adjusted, 0.0, 1.0)
    return output


def _class_mean_difference(matrix: np.ndarray, target: np.ndarray) -> np.ndarray:
    positive = float(target.sum())
    negative = float(len(target) - positive)
    if positive <= 0 or negative <= 0:
        return np.full(matrix.shape[1], np.nan)
    return (target @ matrix) / positive - ((1.0 - target) @ matrix) / negative


def _date_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _mean(values: Any) -> float:
    numeric = pd.to_numeric(values, errors="coerce")
    return float(numeric.mean()) if len(numeric) else np.nan


def _median(values: Any) -> float:
    numeric = pd.to_numeric(values, errors="coerce")
    return float(numeric.median()) if len(numeric) else np.nan


def _safe_divide(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return float(numerator / denominator)
