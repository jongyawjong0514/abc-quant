"""Shadow-only forward outcome labels and monotone probability surfaces.

The module keeps evaluator outcomes separate from prediction frames.  It does
not fit a model or modify a formal strategy.  Missing probabilities remain
missing, and cumulative probabilities are projected onto the ordered surface
``p_ge20 <= p_ge10 <= p_gt0`` before evaluation.

``p_gt0`` is the stable contract name for the complement of ``loss_lt_0``.
It therefore includes an exact zero return so the four outcome buckets remain
mutually exclusive and collectively exhaustive.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd


MODE = "shadow_observation_only"
FORMAL_TRADE_EFFECT = False
TAIL_LOSS_THRESHOLD_PCT = -3.0

OUTCOME_CLASSES = (
    "loss_lt_0",
    "gain_0_10",
    "gain_10_20",
    "gain_ge_20",
)
CUMULATIVE_PROBABILITY_COLUMNS = ("p_gt0", "p_ge10", "p_ge20")
CLASS_PROBABILITY_COLUMNS = (
    "p_loss_lt_0",
    "p_gain_0_10",
    "p_gain_10_20",
    "p_gain_ge_20",
)
TAIL_LABEL_COLUMN = "tail_loss_le_minus3"
TAIL_PROBABILITY_COLUMN = "p_tail_loss_le_minus3"

_PROBABILITY_EPSILON = 1e-12
_SURFACE_TOLERANCE = 1e-12
_SAFE_SURFACE_COLUMNS = {
    *CUMULATIVE_PROBABILITY_COLUMNS,
    *CLASS_PROBABILITY_COLUMNS,
    TAIL_PROBABILITY_COLUMN,
    "probability_surface_complete",
    "tail_probability_available",
    "mode",
    "formal_trade_effect",
}
_EXACT_LABEL_COLUMNS = {
    *OUTCOME_CLASSES,
    TAIL_LABEL_COLUMN,
    "outcome_class",
    "d5_net_return_pct",
}
_LEAKAGE_PREFIXES = (
    "actual_",
    "future_",
    "forward_",
    "label_",
    "realized_",
    "target_",
)
_LEAKAGE_TOKENS = (
    "d5_return",
    "exit_price",
    "gross_return",
    "net_return",
    "outcome_class",
)


def build_forward_outcomes(
    d5_net_returns_pct: Sequence[object] | pd.Series,
) -> pd.DataFrame:
    """Build mutually exclusive D+5 outcome buckets and an independent tail flag.

    Boundaries are ``return < 0``, ``0 <= return < 10``,
    ``10 <= return < 20``, and ``return >= 20``.  The tail flag is true when
    ``return <= -3``.  Missing or non-finite returns stay missing in every
    derived label.
    """

    returns = _as_finite_numeric_series(d5_net_returns_pct, name="d5_net_return_pct")
    valid = returns.notna()
    output = pd.DataFrame(index=returns.index)
    output["d5_net_return_pct"] = returns
    outcome_class = pd.Series(pd.NA, index=returns.index, dtype="string")

    class_masks = {
        "loss_lt_0": returns.lt(0.0),
        "gain_0_10": returns.ge(0.0) & returns.lt(10.0),
        "gain_10_20": returns.ge(10.0) & returns.lt(20.0),
        "gain_ge_20": returns.ge(20.0),
    }
    for outcome, mask in class_masks.items():
        values = pd.Series(pd.NA, index=returns.index, dtype="boolean")
        values.loc[valid] = mask.loc[valid].astype(bool)
        output[outcome] = values
        outcome_class.loc[valid & mask] = outcome

    tail = pd.Series(pd.NA, index=returns.index, dtype="boolean")
    tail.loc[valid] = returns.loc[valid].le(TAIL_LOSS_THRESHOLD_PCT)
    output["outcome_class"] = outcome_class
    output[TAIL_LABEL_COLUMN] = tail
    output["mode"] = MODE
    output["formal_trade_effect"] = FORMAL_TRADE_EFFECT
    _assert_outcome_partition(output)
    return output


def build_monotone_probability_surface(
    raw_probabilities: pd.DataFrame,
    *,
    raw_p_gt0_column: str,
    raw_p_ge10_column: str,
    raw_p_ge20_column: str,
    raw_tail_loss_column: str | None = None,
) -> pd.DataFrame:
    """Project three cumulative probabilities onto a monotone shadow surface.

    Finite raw values are clipped to ``[0, 1]`` and projected by row with
    equal-weight pooled-adjacent-violators regression.  If any cumulative raw
    probability is missing or non-finite, all three cumulative and all four
    class probabilities remain missing for that row.  An optional fourth tail
    probability is clipped independently and is never part of the monotone
    chain.
    """

    required = [raw_p_gt0_column, raw_p_ge10_column, raw_p_ge20_column]
    if raw_tail_loss_column is not None:
        required.append(raw_tail_loss_column)
    missing = sorted(set(required).difference(raw_probabilities.columns))
    if missing:
        raise ValueError("raw probability frame missing columns: " + ", ".join(missing))
    if len(set(required)) != len(required):
        raise ValueError("raw probability columns must be distinct")

    raw_chain = pd.DataFrame(
        {
            "p_gt0": _as_finite_numeric_series(
                raw_probabilities[raw_p_gt0_column], name=raw_p_gt0_column
            ),
            "p_ge10": _as_finite_numeric_series(
                raw_probabilities[raw_p_ge10_column], name=raw_p_ge10_column
            ),
            "p_ge20": _as_finite_numeric_series(
                raw_probabilities[raw_p_ge20_column], name=raw_p_ge20_column
            ),
        },
        index=raw_probabilities.index,
    )
    complete = raw_chain.notna().all(axis=1)
    projected = np.full((len(raw_chain), 3), np.nan, dtype=float)
    complete_positions = np.flatnonzero(complete.to_numpy())
    for position in complete_positions:
        values = raw_chain.iloc[position].to_numpy(dtype=float)
        projected[position] = _project_nonincreasing(np.clip(values, 0.0, 1.0))

    output = pd.DataFrame(
        projected,
        index=raw_probabilities.index,
        columns=CUMULATIVE_PROBABILITY_COLUMNS,
    )
    output["p_loss_lt_0"] = 1.0 - output["p_gt0"]
    output["p_gain_0_10"] = output["p_gt0"] - output["p_ge10"]
    output["p_gain_10_20"] = output["p_ge10"] - output["p_ge20"]
    output["p_gain_ge_20"] = output["p_ge20"]

    if raw_tail_loss_column is None:
        output[TAIL_PROBABILITY_COLUMN] = np.nan
    else:
        raw_tail = _as_finite_numeric_series(
            raw_probabilities[raw_tail_loss_column], name=raw_tail_loss_column
        )
        output[TAIL_PROBABILITY_COLUMN] = raw_tail.clip(lower=0.0, upper=1.0)
    output["probability_surface_complete"] = complete.astype(bool)
    output["tail_probability_available"] = output[TAIL_PROBABILITY_COLUMN].notna()
    output["mode"] = MODE
    output["formal_trade_effect"] = FORMAL_TRADE_EFFECT
    assert_probability_surface(output)
    return output


def evaluate_forward_probability_surface(
    d5_net_returns_pct: Sequence[object] | pd.Series,
    probability_surface: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate cumulative and tail probabilities without imputing missing rows.

    ``calibration_gap`` is the absolute difference between the mean predicted
    probability and the observed event rate.  ``coverage`` is evaluated rows
    divided by rows with a finite outcome.  Empty universes and non-empty
    universes with no evaluable predictions are reported rather than raised.

    The probability frame must be separate from evaluator labels.  Columns
    whose names expose returns, targets, outcomes, or future/realized values are
    rejected before any metric is calculated.
    """

    returns = _as_finite_numeric_series(d5_net_returns_pct, name="d5_net_return_pct")
    if not probability_surface.index.equals(returns.index):
        raise ValueError("probability surface index must exactly match outcome index")
    assert_no_label_leakage_columns(probability_surface.columns)
    assert_probability_surface(probability_surface)

    finite_outcome = returns.notna()
    targets: list[tuple[str, str, pd.Series]] = [
        ("non_loss_ge_0", "p_gt0", returns.ge(0.0)),
        ("gain_ge_10", "p_ge10", returns.ge(10.0)),
        ("gain_ge_20", "p_ge20", returns.ge(20.0)),
    ]
    if TAIL_PROBABILITY_COLUMN in probability_surface:
        targets.append(
            (
                TAIL_LABEL_COLUMN,
                TAIL_PROBABILITY_COLUMN,
                returns.le(TAIL_LOSS_THRESHOLD_PCT),
            )
        )

    records: list[dict[str, Any]] = []
    universe_rows = len(returns)
    label_rows = int(finite_outcome.sum())
    for target_name, probability_column, raw_target in targets:
        probabilities = _strict_probability_column(
            probability_surface, probability_column
        )
        valid = finite_outcome & probabilities.notna()
        evaluation_rows = int(valid.sum())
        metrics = _binary_probability_metrics(
            raw_target.loc[valid].to_numpy(dtype=float),
            probabilities.loc[valid].to_numpy(dtype=float),
        )
        records.append(
            {
                "target": target_name,
                "probability_column": probability_column,
                "universe_rows": universe_rows,
                "label_rows": label_rows,
                "prediction_rows": int(probabilities.notna().sum()),
                "evaluation_rows": evaluation_rows,
                "coverage": evaluation_rows / label_rows if label_rows else 0.0,
                "empty_universe": universe_rows == 0,
                "empty_evaluation": evaluation_rows == 0,
                **metrics,
                "mode": MODE,
                "formal_trade_effect": FORMAL_TRADE_EFFECT,
            }
        )
    return pd.DataFrame(records)


def find_label_leakage_columns(columns: Iterable[object]) -> list[str]:
    """Return columns that expose evaluator-only labels or realized outcomes."""

    leaked: list[str] = []
    for column in columns:
        original = str(column)
        lowered = original.strip().lower()
        if lowered in _SAFE_SURFACE_COLUMNS:
            continue
        if lowered in _EXACT_LABEL_COLUMNS:
            leaked.append(original)
            continue
        if lowered.startswith(_LEAKAGE_PREFIXES):
            leaked.append(original)
            continue
        if any(token in lowered for token in _LEAKAGE_TOKENS):
            leaked.append(original)
    return leaked


def assert_no_label_leakage_columns(columns: Iterable[object]) -> None:
    """Raise when a prediction surface also carries evaluator-only columns."""

    leaked = find_label_leakage_columns(columns)
    if leaked:
        raise ValueError("probability surface contains label leakage columns: " + ", ".join(leaked))


def assert_probability_surface(surface: pd.DataFrame) -> None:
    """Validate bounds, missingness, monotonicity, and optional class identities."""

    missing = sorted(set(CUMULATIVE_PROBABILITY_COLUMNS).difference(surface.columns))
    if missing:
        raise ValueError("probability surface missing columns: " + ", ".join(missing))
    cumulative = pd.DataFrame(
        {
            column: _strict_probability_column(surface, column)
            for column in CUMULATIVE_PROBABILITY_COLUMNS
        },
        index=surface.index,
    )
    partial_missing = cumulative.notna().any(axis=1) & ~cumulative.notna().all(axis=1)
    if partial_missing.any():
        raise ValueError("cumulative probability rows must be complete or entirely missing")
    complete = cumulative.notna().all(axis=1)
    if (
        cumulative.loc[complete, "p_ge20"]
        > cumulative.loc[complete, "p_ge10"] + _SURFACE_TOLERANCE
    ).any() or (
        cumulative.loc[complete, "p_ge10"]
        > cumulative.loc[complete, "p_gt0"] + _SURFACE_TOLERANCE
    ).any():
        raise ValueError("probability surface violates p_ge20 <= p_ge10 <= p_gt0")

    present_class_columns = set(CLASS_PROBABILITY_COLUMNS).intersection(surface.columns)
    if present_class_columns and present_class_columns != set(CLASS_PROBABILITY_COLUMNS):
        missing_class = sorted(set(CLASS_PROBABILITY_COLUMNS).difference(surface.columns))
        raise ValueError("probability surface has partial class columns: " + ", ".join(missing_class))
    if present_class_columns:
        classes = pd.DataFrame(
            {
                column: _strict_probability_column(surface, column)
                for column in CLASS_PROBABILITY_COLUMNS
            },
            index=surface.index,
        )
        expected = pd.DataFrame(
            {
                "p_loss_lt_0": 1.0 - cumulative["p_gt0"],
                "p_gain_0_10": cumulative["p_gt0"] - cumulative["p_ge10"],
                "p_gain_10_20": cumulative["p_ge10"] - cumulative["p_ge20"],
                "p_gain_ge_20": cumulative["p_ge20"],
            },
            index=surface.index,
        )
        difference = (classes - expected).abs()
        if difference.loc[complete].gt(_SURFACE_TOLERANCE).any(axis=None):
            raise ValueError("class probabilities do not match cumulative surface")
        if classes.loc[~complete].notna().any(axis=None):
            raise ValueError("class probabilities must stay missing with cumulative surface")

    if TAIL_PROBABILITY_COLUMN in surface:
        _strict_probability_column(surface, TAIL_PROBABILITY_COLUMN)
    if "mode" in surface:
        modes = surface["mode"].dropna().astype(str)
        if not modes.eq(MODE).all():
            raise ValueError("probability surface must remain shadow_observation_only")
    if "formal_trade_effect" in surface:
        formal = surface["formal_trade_effect"].dropna().astype(bool)
        if formal.any():
            raise ValueError("probability surface cannot have formal trade effect")


def _project_nonincreasing(values: np.ndarray) -> np.ndarray:
    """Return the equal-weight least-squares non-increasing projection."""

    blocks: list[dict[str, float | int]] = []
    for index, value in enumerate(np.asarray(values, dtype=float)):
        blocks.append({"start": index, "end": index + 1, "sum": float(value), "count": 1})
        while len(blocks) >= 2:
            left = blocks[-2]
            right = blocks[-1]
            left_mean = float(left["sum"]) / int(left["count"])
            right_mean = float(right["sum"]) / int(right["count"])
            if left_mean + _SURFACE_TOLERANCE >= right_mean:
                break
            blocks[-2:] = [
                {
                    "start": int(left["start"]),
                    "end": int(right["end"]),
                    "sum": float(left["sum"]) + float(right["sum"]),
                    "count": int(left["count"]) + int(right["count"]),
                }
            ]
    projected = np.empty(len(values), dtype=float)
    for block in blocks:
        mean = float(block["sum"]) / int(block["count"])
        projected[int(block["start"]) : int(block["end"])] = mean
    return np.clip(projected, 0.0, 1.0)


def _strict_probability_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        raise ValueError(f"probability surface missing column: {column}")
    original = frame[column]
    numeric = pd.to_numeric(original, errors="coerce").astype(float)
    invalid_numeric = original.notna() & numeric.isna()
    if invalid_numeric.any() or np.isinf(numeric.to_numpy(dtype=float)).any():
        raise ValueError(f"probability column is not finite numeric: {column}")
    finite = numeric.dropna()
    if ((finite < -_SURFACE_TOLERANCE) | (finite > 1.0 + _SURFACE_TOLERANCE)).any():
        raise ValueError(f"probability column must be within [0, 1]: {column}")
    return numeric


def _binary_probability_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    if len(labels) == 0:
        return {
            "base_rate": np.nan,
            "mean_probability": np.nan,
            "brier": np.nan,
            "logloss": np.nan,
            "calibration_gap": np.nan,
        }
    clipped = np.clip(probabilities, _PROBABILITY_EPSILON, 1.0 - _PROBABILITY_EPSILON)
    base_rate = float(np.mean(labels))
    mean_probability = float(np.mean(probabilities))
    return {
        "base_rate": base_rate,
        "mean_probability": mean_probability,
        "brier": float(np.mean(np.square(probabilities - labels))),
        "logloss": float(
            -np.mean(labels * np.log(clipped) + (1.0 - labels) * np.log1p(-clipped))
        ),
        "calibration_gap": abs(mean_probability - base_rate),
    }


def _as_finite_numeric_series(
    values: Sequence[object] | pd.Series,
    *,
    name: str,
) -> pd.Series:
    if isinstance(values, pd.Series):
        output = pd.to_numeric(values.copy(), errors="coerce").astype(float)
    else:
        output = pd.to_numeric(pd.Series(values), errors="coerce").astype(float)
    output.name = name
    return output.replace([np.inf, -np.inf], np.nan)


def _assert_outcome_partition(outcomes: pd.DataFrame) -> None:
    valid = outcomes["d5_net_return_pct"].notna()
    one_hot = outcomes[list(OUTCOME_CLASSES)].astype("Int64")
    if not one_hot.loc[valid].sum(axis=1).eq(1).all():
        raise AssertionError("finite outcomes must belong to exactly one bucket")
    if one_hot.loc[~valid].notna().any(axis=None):
        raise AssertionError("missing outcomes must keep all bucket labels missing")


__all__ = [
    "CLASS_PROBABILITY_COLUMNS",
    "CUMULATIVE_PROBABILITY_COLUMNS",
    "FORMAL_TRADE_EFFECT",
    "MODE",
    "OUTCOME_CLASSES",
    "TAIL_LABEL_COLUMN",
    "TAIL_LOSS_THRESHOLD_PCT",
    "TAIL_PROBABILITY_COLUMN",
    "assert_no_label_leakage_columns",
    "assert_probability_surface",
    "build_forward_outcomes",
    "build_monotone_probability_surface",
    "evaluate_forward_probability_surface",
    "find_label_leakage_columns",
]
