"""Contracts for deterministic pipeline diagnostic summaries."""

from __future__ import annotations

from typing import Any, Final

MODELING_SMOKE_SUMMARY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "row_count",
        "ticker_count",
        "rows_per_ticker",
        "feature_columns",
        "label_column",
        "label_non_missing_count",
        "label_missing_count",
        "split_counts",
        "fitted_value",
        "baseline_method",
        "training_label_count",
        "evaluation",
    }
)

MODELING_SMOKE_BASELINE_METHODS: Final[frozenset[str]] = frozenset(
    {"mean", "median"}
)

MODELING_SMOKE_EVALUATION_SPLITS: Final[frozenset[str]] = frozenset(
    {"train", "validation", "test"}
)

EVALUATION_METRIC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "split_name",
        "row_count",
        "non_missing_count",
        "missing_actual_count",
        "mae",
        "rmse",
        "mean_error",
        "prediction_mean",
    }
)


def validate_modeling_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the deterministic modeling smoke summary shape.

    The function returns the original summary object unchanged when valid.
    """
    if not isinstance(summary, dict):
        raise ValueError("modeling smoke summary must be a dict")

    _validate_key_set(
        "modeling smoke summary",
        actual_keys=summary.keys(),
        expected_keys=MODELING_SMOKE_SUMMARY_KEYS,
    )

    if summary["baseline_method"] not in MODELING_SMOKE_BASELINE_METHODS:
        raise ValueError(
            "modeling smoke summary baseline_method must be one of: mean, median"
        )

    evaluation = summary["evaluation"]
    if not isinstance(evaluation, dict):
        raise ValueError("modeling smoke summary evaluation must be a dict")

    _validate_key_set(
        "modeling smoke summary evaluation",
        actual_keys=evaluation.keys(),
        expected_keys=MODELING_SMOKE_EVALUATION_SPLITS,
    )

    for split_name in sorted(MODELING_SMOKE_EVALUATION_SPLITS):
        metrics = evaluation[split_name]
        if not isinstance(metrics, dict):
            raise ValueError(f"evaluation metrics for {split_name} must be a dict")
        _validate_key_set(
            f"evaluation metrics for {split_name}",
            actual_keys=metrics.keys(),
            expected_keys=EVALUATION_METRIC_KEYS,
        )

    return summary


def _validate_key_set(
    context: str,
    *,
    actual_keys: object,
    expected_keys: frozenset[str],
) -> None:
    actual = {str(key) for key in actual_keys}
    missing = sorted(expected_keys - actual)
    unknown = sorted(actual - expected_keys)
    if missing or unknown:
        raise ValueError(
            f"{context} keys mismatch: "
            f"missing={missing}; unknown={unknown}"
        )
