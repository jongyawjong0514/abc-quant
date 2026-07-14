"""Point-in-time grouping helpers for shadow-only Taiwan equity research.

The module deliberately separates grouping from signal generation.  It never
uses outcome columns, never backfills current concept membership into history,
and never substitutes paid-in capital for free-float market capitalisation.
Percentiles are expressed on the ``[0, 1]`` scale within each observation day.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd


MODE = "shadow_observation_only"
FORMAL_TRADE_EFFECT = False
INSUFFICIENT_DATA = "insufficient_data"
INSUFFICIENT_FEATURES = "INSUFFICIENT_FEATURES"

ALLOWED_MARKET_REGIMES = frozenset(
    f"trend_{trend}_volatility_{volatility}"
    for trend in ("up", "flat", "down")
    for volatility in ("high", "low")
)


def asof_join_point_in_time(
    observations: pd.DataFrame,
    features: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    by: Sequence[str] = ("stock_id",),
    observation_date_column: str = "observation_date",
    effective_date_column: str = "effective_date",
    available_date_column: str | None = None,
    prefix: str = "feature",
) -> pd.DataFrame:
    """Attach the latest feature row available at each observation date.

    A source row becomes usable on the later of its effective and available
    dates.  Future-only rows remain unmatched with ``insufficient_data``;
    they are never selected or backfilled.  Duplicate source keys at the same
    PIT source date are rejected because their ordering would be ambiguous.
    """

    if not prefix:
        raise ValueError("prefix must not be empty")
    key_columns = list(by)
    if not key_columns:
        raise ValueError("by must contain at least one key column")
    selected_columns = list(feature_columns)
    if not selected_columns:
        raise ValueError("feature_columns must not be empty")

    _require_columns(
        observations,
        [observation_date_column, *key_columns],
        label="observations",
    )
    source_required = [effective_date_column, *key_columns, *selected_columns]
    if available_date_column is not None:
        source_required.append(available_date_column)
    _require_columns(features, source_required, label="features")

    collisions = set(selected_columns) & set(observations.columns)
    if collisions:
        raise ValueError(
            "feature columns already exist in observations: "
            + ", ".join(sorted(collisions))
        )
    if observations[key_columns].isna().any(axis=None):
        raise ValueError("observation PIT keys must not be missing")
    if features[key_columns].isna().any(axis=None):
        raise ValueError("feature PIT keys must not be missing")

    output = observations.copy()
    observation_dates = _datetime_series(
        output[observation_date_column],
        label=f"observations.{observation_date_column}",
        allow_missing=False,
    )
    output[observation_date_column] = observation_dates
    source = features.copy()
    effective_dates = _datetime_series(
        source[effective_date_column],
        label=f"features.{effective_date_column}",
        allow_missing=False,
    )
    source[effective_date_column] = effective_dates
    if available_date_column is None:
        available_dates = pd.Series(pd.NaT, index=source.index, dtype="datetime64[ns]")
    else:
        available_dates = _datetime_series(
            source[available_date_column],
            label=f"features.{available_date_column}",
            allow_missing=True,
        )
        source[available_date_column] = available_dates
    source["_pit_source_date"] = pd.concat(
        [effective_dates, available_dates], axis=1
    ).max(axis=1)

    duplicate_keys = [*key_columns, "_pit_source_date"]
    duplicates = source.duplicated(duplicate_keys, keep=False)
    if duplicates.any():
        raise ValueError(
            "features contain ambiguous duplicate PIT keys: "
            f"{int(duplicates.sum())} rows"
        )

    row_count = len(output)
    feature_values: dict[str, np.ndarray] = {
        column: np.full(row_count, np.nan, dtype=object)
        for column in selected_columns
    }
    nat_ns = np.datetime64("NaT", "ns")
    source_dates = np.full(row_count, nat_ns, dtype="datetime64[ns]")
    selected_effective = np.full(
        row_count, nat_ns, dtype="datetime64[ns]"
    )
    selected_available = np.full(
        row_count, nat_ns, dtype="datetime64[ns]"
    )
    statuses = np.full(row_count, INSUFFICIENT_DATA, dtype=object)

    left = output.copy()
    left["_pit_row_id"] = np.arange(row_count, dtype=int)
    right_groups = {
        _normalized_group_key(key): group
        for key, group in _groupby(source, key_columns)
    }
    for raw_key, left_group in _groupby(left, key_columns):
        right_group = right_groups.get(_normalized_group_key(raw_key))
        if right_group is None or right_group.empty:
            continue
        left_part = left_group[["_pit_row_id", observation_date_column]].sort_values(
            observation_date_column
        )
        right_columns = [
            "_pit_source_date",
            effective_date_column,
            *selected_columns,
        ]
        if available_date_column is not None:
            right_columns.append(available_date_column)
        right_part = right_group[right_columns].sort_values("_pit_source_date")
        joined = pd.merge_asof(
            left_part,
            right_part,
            left_on=observation_date_column,
            right_on="_pit_source_date",
            direction="backward",
            allow_exact_matches=True,
        )
        matched = joined["_pit_source_date"].notna()
        if not matched.any():
            continue
        matched_rows = joined.loc[matched]
        row_ids = matched_rows["_pit_row_id"].to_numpy(dtype=int)
        observed = matched_rows[observation_date_column]
        if (matched_rows["_pit_source_date"] > observed).any():
            raise AssertionError("future PIT source date was selected")
        if (matched_rows[effective_date_column] > observed).any():
            raise AssertionError("future effective date was selected")
        if available_date_column is not None:
            selected_available_dates = matched_rows[available_date_column]
            if (
                selected_available_dates.notna()
                & selected_available_dates.gt(observed)
            ).any():
                raise AssertionError("future available date was selected")
            selected_available[row_ids] = selected_available_dates.to_numpy(
                dtype="datetime64[ns]"
            )
        for column in selected_columns:
            feature_values[column][row_ids] = matched_rows[column].to_numpy()
        source_dates[row_ids] = matched_rows["_pit_source_date"].to_numpy(
            dtype="datetime64[ns]"
        )
        selected_effective[row_ids] = matched_rows[effective_date_column].to_numpy(
            dtype="datetime64[ns]"
        )
        statuses[row_ids] = "point_in_time"

    for column, values in feature_values.items():
        output[column] = values
    output[f"{prefix}_source_date"] = pd.to_datetime(source_dates)
    output[f"{prefix}_effective_date"] = pd.to_datetime(selected_effective)
    if available_date_column is not None:
        output[f"{prefix}_available_date"] = pd.to_datetime(selected_available)
    output[f"{prefix}_pit_status"] = statuses
    return output


def attach_score_percentiles(
    rows: pd.DataFrame,
    *,
    score_column: str = "score",
    date_column: str = "observation_date",
    sector_column: str = "sector",
) -> pd.DataFrame:
    """Attach same-day market and same-day-within-sector score percentiles."""

    _require_columns(rows, [date_column, score_column, sector_column], label="rows")
    output = rows.copy()
    output[date_column] = _datetime_series(
        output[date_column], label=f"rows.{date_column}", allow_missing=False
    )
    score = pd.to_numeric(output[score_column], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    output["market_percentile"] = score.groupby(output[date_column]).rank(
        method="average", pct=True
    )
    output["sector_within_percentile"] = np.nan
    sector = output[sector_column].fillna("").astype(str).str.strip()
    valid = score.notna() & sector.ne("") & sector.ne(INSUFFICIENT_FEATURES)
    if valid.any():
        output.loc[valid, "sector_within_percentile"] = score.loc[valid].groupby(
            [output.loc[valid, date_column], sector.loc[valid]]
        ).rank(method="average", pct=True)
    return output


def attach_cross_sectional_size_and_liquidity(
    rows: pd.DataFrame,
    *,
    date_column: str = "observation_date",
    free_float_market_cap_column: str = "free_float_market_cap",
    liquidity_column: str = "avg_turnover_20_twd",
) -> pd.DataFrame:
    """Attach daily free-float size and liquidity tertiles.

    At least three valid positive observations are required for a daily
    cross-section.  Missing free-float market capitalisation is never replaced
    with paid-in capital or any other balance-sheet scale proxy.
    """

    _require_columns(rows, [date_column], label="rows")
    output = rows.copy()
    output[date_column] = _datetime_series(
        output[date_column], label=f"rows.{date_column}", allow_missing=False
    )
    size = _positive_numeric_column(output, free_float_market_cap_column)
    liquidity = _positive_numeric_column(output, liquidity_column)
    output["size_percentile"] = _daily_percentile_with_minimum_count(
        size, output[date_column], minimum_count=3
    )
    output["size_tier"] = _tertile_labels(
        output["size_percentile"], labels=("small", "mid", "large")
    )
    output["liquidity_percentile"] = _daily_percentile_with_minimum_count(
        liquidity, output[date_column], minimum_count=3
    )
    output["liquidity_tier"] = _tertile_labels(
        output["liquidity_percentile"], labels=("low", "mid", "high")
    )
    return output


def attach_market_regime(
    rows: pd.DataFrame,
    *,
    trend_column: str = "market_trend",
    volatility_column: str = "market_volatility",
) -> pd.DataFrame:
    """Compose only the six allowed trend-by-volatility market regimes."""

    output = rows.copy()
    trend = _normalized_state_column(output, trend_column, prefix="trend_")
    volatility = _normalized_state_column(
        output, volatility_column, prefix="volatility_"
    )
    regime = "trend_" + trend + "_volatility_" + volatility
    output["market_regime"] = regime.where(
        regime.isin(ALLOWED_MARKET_REGIMES), INSUFFICIENT_FEATURES
    )
    return output


def attach_concept_membership(
    observations: pd.DataFrame,
    concept_history: pd.DataFrame,
    *,
    observation_date_column: str = "observation_date",
    stock_column: str = "stock_id",
    concept_column: str = "concept",
    snapshot_date_column: str = "snapshot_date",
    effective_date_column: str = "effective_date",
    available_date_column: str = "available_date",
    membership_mode_column: str = "membership_mode",
) -> pd.DataFrame:
    """Attach the latest valid concept snapshot without current backfill."""

    _require_columns(
        observations,
        [observation_date_column, stock_column],
        label="observations",
    )
    output = observations.copy()
    output[observation_date_column] = _datetime_series(
        output[observation_date_column],
        label=f"observations.{observation_date_column}",
        allow_missing=False,
    )
    concepts: list[tuple[str, ...]] = [tuple() for _ in range(len(output))]
    statuses = np.full(len(output), INSUFFICIENT_DATA, dtype=object)
    source_dates = np.full(
        len(output), np.datetime64("NaT", "ns"), dtype="datetime64[ns]"
    )
    if concept_history.empty:
        output["concepts"] = concepts
        output["concept_status"] = statuses
        output["concept_source_date"] = pd.to_datetime(source_dates)
        return output

    _require_columns(concept_history, [stock_column, concept_column], label="concepts")
    source = concept_history.copy()
    date_columns = [
        column
        for column in (
            snapshot_date_column,
            effective_date_column,
            available_date_column,
        )
        if column in source.columns
    ]
    if not any(
        column in source.columns
        for column in (snapshot_date_column, effective_date_column)
    ):
        output["concepts"] = concepts
        output["concept_status"] = statuses
        output["concept_source_date"] = pd.to_datetime(source_dates)
        return output
    parsed_dates: list[pd.Series] = []
    for column in date_columns:
        parsed = _datetime_series(
            source[column], label=f"concepts.{column}", allow_missing=True
        )
        source[column] = parsed
        parsed_dates.append(parsed)
    source["_concept_source_date"] = pd.concat(parsed_dates, axis=1).max(axis=1)
    source = source[source["_concept_source_date"].notna()].copy()
    if membership_mode_column in source.columns:
        modes = source[membership_mode_column].fillna("").astype(str).str.lower()
        forbidden = modes.str.contains("backfill", regex=False) | modes.str.contains(
            "static_current", regex=False
        )
        source = source.loc[~forbidden].copy()
    if source.empty:
        output["concepts"] = concepts
        output["concept_status"] = statuses
        output["concept_source_date"] = pd.to_datetime(source_dates)
        return output

    source_groups = {
        str(stock_id): group
        for stock_id, group in source.groupby(stock_column, sort=False)
    }
    for row_position, (_, observation) in enumerate(output.iterrows()):
        candidates = source_groups.get(str(observation[stock_column]))
        if candidates is None:
            continue
        observation_date = observation[observation_date_column]
        available = candidates[
            candidates["_concept_source_date"].le(observation_date)
        ]
        if available.empty:
            continue
        latest_date = available["_concept_source_date"].max()
        latest = available[available["_concept_source_date"].eq(latest_date)]
        names = tuple(
            sorted(
                {
                    str(value).strip()
                    for value in latest[concept_column]
                    if pd.notna(value) and str(value).strip()
                }
            )
        )
        if not names:
            continue
        concepts[row_position] = names
        statuses[row_position] = "point_in_time"
        source_dates[row_position] = np.datetime64(latest_date.to_datetime64(), "ns")

    output["concepts"] = concepts
    output["concept_status"] = statuses
    output["concept_source_date"] = pd.to_datetime(source_dates)
    future = output["concept_source_date"].notna() & output[
        "concept_source_date"
    ].gt(output[observation_date_column])
    if future.any():
        raise AssertionError("future concept snapshot was selected")
    return output


def build_pit_groupings(
    observations: pd.DataFrame,
    *,
    sector_history: pd.DataFrame,
    concept_history: pd.DataFrame | None = None,
    score_column: str = "score",
    observation_date_column: str = "observation_date",
    stock_column: str = "stock_id",
    sector_column: str = "sector",
    sector_effective_date_column: str = "effective_date",
    sector_available_date_column: str = "available_date",
    free_float_market_cap_column: str = "free_float_market_cap",
    liquidity_column: str = "avg_turnover_20_twd",
    trend_column: str = "market_trend",
    volatility_column: str = "market_volatility",
) -> pd.DataFrame:
    """Build the complete independent PIT grouping sidecar."""

    _require_columns(
        observations,
        [observation_date_column, stock_column, score_column],
        label="observations",
    )
    base = observations.drop(columns=[sector_column], errors="ignore")
    available_column = (
        sector_available_date_column
        if sector_available_date_column in sector_history.columns
        else None
    )
    output = asof_join_point_in_time(
        base,
        sector_history,
        feature_columns=[sector_column],
        by=[stock_column],
        observation_date_column=observation_date_column,
        effective_date_column=sector_effective_date_column,
        available_date_column=available_column,
        prefix="sector",
    )
    sector_valid = output["sector_pit_status"].eq("point_in_time")
    sector_text = output[sector_column].fillna("").astype(str).str.strip()
    output[sector_column] = sector_text.where(
        sector_valid & sector_text.ne(""), INSUFFICIENT_FEATURES
    )
    output = attach_score_percentiles(
        output,
        score_column=score_column,
        date_column=observation_date_column,
        sector_column=sector_column,
    )
    output = attach_cross_sectional_size_and_liquidity(
        output,
        date_column=observation_date_column,
        free_float_market_cap_column=free_float_market_cap_column,
        liquidity_column=liquidity_column,
    )
    output = attach_market_regime(
        output,
        trend_column=trend_column,
        volatility_column=volatility_column,
    )
    if concept_history is None:
        output["concepts"] = pd.Series(
            [tuple() for _ in range(len(output))], index=output.index, dtype="object"
        )
        output["concept_status"] = INSUFFICIENT_DATA
        output["concept_source_date"] = pd.NaT
    else:
        output = attach_concept_membership(
            output,
            concept_history,
            observation_date_column=observation_date_column,
            stock_column=stock_column,
        )
    output["grouping_mode"] = MODE
    output["formal_trade_effect"] = FORMAL_TRADE_EFFECT
    return output


def beta_binomial_partial_pool(
    groups: pd.DataFrame,
    *,
    successes_column: str = "successes",
    trials_column: str = "trials",
    prior_strength: float = 20.0,
    prior_mean: float | None = None,
) -> pd.DataFrame:
    """Shrink group hit rates toward a shared beta-binomial prior.

    When ``prior_mean`` is omitted, a Jeffreys-smoothed pooled rate is used.
    Zero-trial groups receive the prior mean and are labelled ``prior_only``.
    """

    _require_columns(groups, [successes_column, trials_column], label="groups")
    if not np.isfinite(prior_strength) or prior_strength <= 0.0:
        raise ValueError("prior_strength must be finite and positive")
    output = groups.copy()
    successes = pd.to_numeric(output[successes_column], errors="raise").astype(float)
    trials = pd.to_numeric(output[trials_column], errors="raise").astype(float)
    invalid = (
        ~np.isfinite(successes)
        | ~np.isfinite(trials)
        | successes.lt(0.0)
        | trials.lt(0.0)
        | successes.gt(trials)
    )
    if invalid.any():
        raise ValueError("successes and trials must satisfy 0 <= successes <= trials")
    total_trials = float(trials.sum())
    if prior_mean is None:
        total_successes = float(successes.sum())
        resolved_prior_mean = (total_successes + 0.5) / (total_trials + 1.0)
    else:
        resolved_prior_mean = float(prior_mean)
    if not np.isfinite(resolved_prior_mean) or not 0.0 < resolved_prior_mean < 1.0:
        raise ValueError("prior_mean must be finite and strictly between zero and one")
    prior_alpha = resolved_prior_mean * float(prior_strength)
    prior_beta = (1.0 - resolved_prior_mean) * float(prior_strength)
    output["raw_rate"] = successes.div(trials.where(trials.gt(0.0)))
    output["prior_mean"] = resolved_prior_mean
    output["posterior_alpha"] = successes + prior_alpha
    output["posterior_beta"] = trials - successes + prior_beta
    output["pooled_rate"] = output["posterior_alpha"] / (
        output["posterior_alpha"] + output["posterior_beta"]
    )
    output["partial_pool_status"] = np.where(
        trials.gt(0.0), "partial_pool", "prior_only"
    )
    return output


def _positive_numeric_column(rows: pd.DataFrame, column: str) -> pd.Series:
    if column not in rows.columns:
        return pd.Series(np.nan, index=rows.index, dtype=float)
    values = pd.to_numeric(rows[column], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    return values.where(values.gt(0.0))


def _daily_percentile_with_minimum_count(
    values: pd.Series,
    dates: pd.Series,
    *,
    minimum_count: int,
) -> pd.Series:
    valid_count = values.notna().groupby(dates).transform("sum")
    percentile = values.groupby(dates).rank(method="average", pct=True)
    return percentile.where(valid_count.ge(minimum_count))


def _tertile_labels(
    percentile: pd.Series, *, labels: tuple[str, str, str]
) -> pd.Series:
    output = pd.Series(INSUFFICIENT_FEATURES, index=percentile.index, dtype="object")
    valid = percentile.notna()
    output.loc[valid & percentile.le(1.0 / 3.0)] = labels[0]
    output.loc[valid & percentile.gt(1.0 / 3.0) & percentile.le(2.0 / 3.0)] = labels[1]
    output.loc[valid & percentile.gt(2.0 / 3.0)] = labels[2]
    return output


def _normalized_state_column(
    rows: pd.DataFrame, column: str, *, prefix: str
) -> pd.Series:
    if column not in rows.columns:
        return pd.Series("", index=rows.index, dtype="object")
    normalized = rows[column].fillna("").astype(str).str.strip().str.lower()
    return normalized.str.removeprefix(prefix)


def _datetime_series(
    values: pd.Series, *, label: str, allow_missing: bool
) -> pd.Series:
    try:
        parsed = pd.to_datetime(values, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} contains an invalid datetime") from exc
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_convert("UTC").dt.tz_localize(None)
    parsed = parsed.astype("datetime64[ns]")
    if not allow_missing and parsed.isna().any():
        raise ValueError(f"{label} must not contain missing dates")
    return parsed


def _groupby(
    frame: pd.DataFrame, columns: list[str]
) -> Iterable[tuple[Any, pd.DataFrame]]:
    grouper: str | list[str] = columns[0] if len(columns) == 1 else columns
    return frame.groupby(grouper, sort=False, dropna=False)


def _normalized_group_key(value: Any) -> tuple[Any, ...]:
    return value if isinstance(value, tuple) else (value,)


def _require_columns(
    frame: pd.DataFrame, columns: Iterable[str], *, label: str
) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")
