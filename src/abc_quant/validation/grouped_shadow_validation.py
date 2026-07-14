"""Grouped shadow validation with small-sample shrinkage.

The helpers in this module are descriptive research tools.  They do not select
formal trades or promote a strategy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BetaBinomialPrior:
    """Moment-matched empirical-Bayes prior for grouped hit rates."""

    alpha: float
    beta: float
    mean: float
    strength: float
    group_count: int
    method: str


def estimate_beta_binomial_prior(
    successes: pd.Series | np.ndarray,
    totals: pd.Series | np.ndarray,
    *,
    fallback_strength: float = 20.0,
    maximum_strength: float = 1000.0,
) -> BetaBinomialPrior:
    """Estimate a conservative beta prior after removing binomial sampling noise."""

    success = np.asarray(successes, dtype=float)
    total = np.asarray(totals, dtype=float)
    if success.shape != total.shape:
        raise ValueError("successes and totals must have the same shape")
    valid = (
        np.isfinite(success)
        & np.isfinite(total)
        & (total > 0.0)
        & (success >= 0.0)
        & (success <= total)
    )
    success = success[valid]
    total = total[valid]
    if total.size == 0:
        raise ValueError("at least one valid group is required")
    if not np.isfinite(fallback_strength) or fallback_strength <= 0.0:
        raise ValueError("fallback_strength must be positive")
    if not np.isfinite(maximum_strength) or maximum_strength < fallback_strength:
        raise ValueError("maximum_strength must be at least fallback_strength")

    epsilon = 1e-6
    pooled_mean = float(np.clip(success.sum() / total.sum(), epsilon, 1.0 - epsilon))
    rates = success / total
    method = "fallback"
    strength = float(fallback_strength)
    if total.size >= 3:
        observed_variance = float(np.var(rates, ddof=1))
        average_sampling_variance = float(
            np.mean(pooled_mean * (1.0 - pooled_mean) / total)
        )
        between_group_variance = observed_variance - average_sampling_variance
        if between_group_variance > 1e-10:
            implied_strength = (
                pooled_mean * (1.0 - pooled_mean) / between_group_variance - 1.0
            )
            strength = float(
                np.clip(implied_strength, fallback_strength, maximum_strength)
            )
            method = "moment_matched"
        elif observed_variance <= average_sampling_variance:
            strength = float(maximum_strength)
            method = "sampling_noise_dominates"

    return BetaBinomialPrior(
        alpha=pooled_mean * strength,
        beta=(1.0 - pooled_mean) * strength,
        mean=pooled_mean,
        strength=strength,
        group_count=int(total.size),
        method=method,
    )


def beta_posterior_summary(
    successes: int | float,
    total: int | float,
    prior: BetaBinomialPrior,
    *,
    z_value: float = 1.959963984540054,
) -> dict[str, float]:
    """Return beta posterior mean and a normal-approximation credible interval."""

    success = float(successes)
    count = float(total)
    if not np.isfinite(success) or not np.isfinite(count):
        raise ValueError("successes and total must be finite")
    if count < 0.0 or success < 0.0 or success > count:
        raise ValueError("successes must be between zero and total")
    posterior_alpha = prior.alpha + success
    posterior_beta = prior.beta + count - success
    posterior_total = posterior_alpha + posterior_beta
    mean = posterior_alpha / posterior_total
    variance = (
        posterior_alpha
        * posterior_beta
        / (posterior_total**2 * (posterior_total + 1.0))
    )
    standard_deviation = float(np.sqrt(max(variance, 0.0)))
    return {
        "posterior_precision": float(mean),
        "posterior_precision_lower": float(
            np.clip(mean - z_value * standard_deviation, 0.0, 1.0)
        ),
        "posterior_precision_upper": float(
            np.clip(mean + z_value * standard_deviation, 0.0, 1.0)
        ),
        "posterior_standard_deviation": standard_deviation,
    }


def build_grouped_strategy_metrics(
    rows: pd.DataFrame,
    *,
    group_column: str,
    strategies: Mapping[str, str | None],
    date_column: str = "asof_date",
    stock_column: str = "stock_id",
    target_column: str = "target_gain_ge10",
    return_column: str = "net_return_pct",
    tail_loss_threshold: float = -3.0,
    fallback_prior_strength: float = 20.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build raw and partially pooled metrics for every strategy/group pair."""

    required = {
        group_column,
        date_column,
        stock_column,
        target_column,
        return_column,
        *(column for column in strategies.values() if column is not None),
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"grouped metrics missing columns: {sorted(missing)}")
    if rows.empty:
        return pd.DataFrame(), pd.DataFrame()
    work = rows.copy()
    if work[group_column].isna().any():
        raise ValueError(f"{group_column} contains missing values")
    work[target_column] = work[target_column].fillna(False).astype(bool)
    work[return_column] = pd.to_numeric(work[return_column], errors="raise")
    if not np.isfinite(work[return_column]).all():
        raise ValueError("return column must be finite")

    group_base = (
        work.groupby(group_column, observed=True)
        .agg(
            eligible_rows=(target_column, "size"),
            eligible_gain_rows=(target_column, "sum"),
            eligible_gain_rate=(target_column, "mean"),
        )
        .reset_index()
    )
    records: list[dict[str, object]] = []
    priors: list[dict[str, object]] = []
    for strategy, selection_column in strategies.items():
        selected = (
            pd.Series(True, index=work.index)
            if selection_column is None
            else work[selection_column].fillna(False).astype(bool)
        )
        chosen = work.loc[selected].copy()
        grouped = (
            chosen.groupby(group_column, observed=True)
            .agg(
                selected_rows=(target_column, "size"),
                selected_gain_rows=(target_column, "sum"),
                selected_gain_rate=(target_column, "mean"),
                selected_trading_days=(date_column, "nunique"),
                selected_stocks=(stock_column, "nunique"),
                selected_mean_net_return_pct=(return_column, "mean"),
                selected_median_net_return_pct=(return_column, "median"),
                selected_loss_rate=(return_column, lambda values: float((values < 0).mean())),
                selected_tail_loss_rate=(
                    return_column,
                    lambda values: float((values <= tail_loss_threshold).mean()),
                ),
            )
            .reset_index()
        )
        grouped = group_base.merge(grouped, on=group_column, how="left")
        count_columns = [
            "selected_rows",
            "selected_gain_rows",
            "selected_trading_days",
            "selected_stocks",
        ]
        grouped[count_columns] = grouped[count_columns].fillna(0).astype(int)
        prior_input = grouped[grouped["selected_rows"].gt(0)]
        prior = estimate_beta_binomial_prior(
            prior_input["selected_gain_rows"],
            prior_input["selected_rows"],
            fallback_strength=fallback_prior_strength,
        )
        priors.append({"strategy": strategy, **asdict(prior)})
        total_selected = int(grouped["selected_rows"].sum())
        total_hits = int(grouped["selected_gain_rows"].sum())
        for row in grouped.itertuples(index=False):
            posterior = beta_posterior_summary(
                row.selected_gain_rows,
                row.selected_rows,
                prior,
            )
            raw_precision = (
                float(row.selected_gain_rows / row.selected_rows)
                if row.selected_rows
                else np.nan
            )
            records.append(
                {
                    "strategy": strategy,
                    group_column: getattr(row, group_column),
                    "eligible_rows": int(row.eligible_rows),
                    "eligible_gain_rows": int(row.eligible_gain_rows),
                    "eligible_gain_rate": float(row.eligible_gain_rate),
                    "selected_rows": int(row.selected_rows),
                    "selected_gain_rows": int(row.selected_gain_rows),
                    "selected_gain_rate": raw_precision,
                    **posterior,
                    "raw_minus_posterior_precision": raw_precision
                    - posterior["posterior_precision"]
                    if np.isfinite(raw_precision)
                    else np.nan,
                    "precision_lift_vs_group_base": raw_precision
                    / float(row.eligible_gain_rate)
                    if np.isfinite(raw_precision) and row.eligible_gain_rate > 0
                    else np.nan,
                    "selected_trading_days": int(row.selected_trading_days),
                    "selected_stocks": int(row.selected_stocks),
                    "selected_mean_net_return_pct": float(
                        row.selected_mean_net_return_pct
                    ),
                    "selected_median_net_return_pct": float(
                        row.selected_median_net_return_pct
                    ),
                    "selected_loss_rate": float(row.selected_loss_rate),
                    "selected_tail_loss_rate": float(row.selected_tail_loss_rate),
                    "selected_share_of_strategy": int(row.selected_rows)
                    / total_selected
                    if total_selected
                    else 0.0,
                    "gain_share_of_strategy": int(row.selected_gain_rows) / total_hits
                    if total_hits
                    else 0.0,
                    "prior_mean": prior.mean,
                    "prior_strength": prior.strength,
                    "prior_method": prior.method,
                }
            )
    output = pd.DataFrame(records)
    if not output.empty:
        output = output.sort_values(
            ["strategy", "posterior_precision", "selected_rows", group_column],
            ascending=[True, False, False, True],
        ).reset_index(drop=True)
    return output, pd.DataFrame(priors)


__all__ = [
    "BetaBinomialPrior",
    "beta_posterior_summary",
    "build_grouped_strategy_metrics",
    "estimate_beta_binomial_prior",
]
