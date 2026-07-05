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

PREPROCESSING_SMOKE_SUMMARY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "row_count",
        "feature_columns",
        "split_counts",
        "fitted_means",
        "fitted_stds",
        "train_mean_after_scaling",
        "train_std_after_scaling",
        "split_shape",
    }
)

PREPROCESSING_SMOKE_SPLITS: Final[frozenset[str]] = frozenset(
    {"train", "validation", "test"}
)

PREPROCESSING_SMOKE_SPLIT_SHAPE_KEYS: Final[frozenset[str]] = frozenset(
    {"rows", "columns"}
)

SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "row_count",
        "feature_columns",
        "label_column",
        "split_counts_before_label_drop",
        "split_counts_after_label_drop",
        "dropped_label_counts",
        "split_shape",
    }
)

SUPERVISED_DATASET_SMOKE_SPLITS: Final[frozenset[str]] = frozenset(
    {"train", "validation", "test"}
)

SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS: Final[frozenset[str]] = frozenset(
    {"rows", "columns"}
)

LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "row_count",
        "feature_columns",
        "label_column",
        "model_name",
        "method",
        "intercept",
        "coefficients",
        "training_row_count",
        "split_counts_after_label_drop",
        "dropped_label_counts",
        "prediction_counts",
        "evaluation",
    }
)

LINEAR_REGRESSION_SMOKE_SPLITS: Final[frozenset[str]] = frozenset(
    {"train", "validation", "test"}
)

LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS: Final[frozenset[str]] = (
    EVALUATION_METRIC_KEYS
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


def validate_preprocessing_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the deterministic preprocessing smoke summary shape.

    The function returns the original summary object unchanged when valid.
    """
    if not isinstance(summary, dict):
        raise ValueError("preprocessing smoke summary must be a dict")

    _validate_key_set(
        "preprocessing smoke summary",
        actual_keys=summary.keys(),
        expected_keys=PREPROCESSING_SMOKE_SUMMARY_KEYS,
    )

    split_counts = summary["split_counts"]
    if not isinstance(split_counts, dict):
        raise ValueError("preprocessing smoke summary split_counts must be a dict")
    _validate_key_set(
        "preprocessing smoke summary split_counts",
        actual_keys=split_counts.keys(),
        expected_keys=PREPROCESSING_SMOKE_SPLITS,
    )

    split_shape = summary["split_shape"]
    if not isinstance(split_shape, dict):
        raise ValueError("preprocessing smoke summary split_shape must be a dict")
    _validate_key_set(
        "preprocessing smoke summary split_shape",
        actual_keys=split_shape.keys(),
        expected_keys=PREPROCESSING_SMOKE_SPLITS,
    )

    for split_name in sorted(PREPROCESSING_SMOKE_SPLITS):
        shape = split_shape[split_name]
        if not isinstance(shape, dict):
            raise ValueError(f"split_shape for {split_name} must be a dict")
        _validate_key_set(
            f"split_shape for {split_name}",
            actual_keys=shape.keys(),
            expected_keys=PREPROCESSING_SMOKE_SPLIT_SHAPE_KEYS,
        )

    return summary


def validate_linear_regression_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the deterministic OLS smoke summary shape.

    The function returns the original summary object unchanged when valid.
    """
    if not isinstance(summary, dict):
        raise ValueError("linear regression smoke summary must be a dict")

    _validate_key_set(
        "linear regression smoke summary",
        actual_keys=summary.keys(),
        expected_keys=LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS,
    )

    if not isinstance(summary["feature_columns"], list):
        raise ValueError("linear regression smoke summary feature_columns must be a list")
    if not isinstance(summary["coefficients"], dict):
        raise ValueError("linear regression smoke summary coefficients must be a dict")

    _validate_linear_regression_split_mapping(
        summary,
        "split_counts_after_label_drop",
    )
    _validate_linear_regression_split_mapping(summary, "dropped_label_counts")
    _validate_linear_regression_split_mapping(summary, "prediction_counts")

    evaluation = summary["evaluation"]
    if not isinstance(evaluation, dict):
        raise ValueError("linear regression smoke summary evaluation must be a dict")
    _validate_key_set(
        "linear regression smoke summary evaluation",
        actual_keys=evaluation.keys(),
        expected_keys=LINEAR_REGRESSION_SMOKE_SPLITS,
    )

    for split_name in sorted(LINEAR_REGRESSION_SMOKE_SPLITS):
        metrics = evaluation[split_name]
        if not isinstance(metrics, dict):
            raise ValueError(f"linear regression metrics for {split_name} must be a dict")
        _validate_key_set(
            f"linear regression metrics for {split_name}",
            actual_keys=metrics.keys(),
            expected_keys=LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS,
        )

    return summary


def validate_supervised_dataset_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the deterministic supervised dataset smoke summary shape.

    The function returns the original summary object unchanged when valid.
    """
    if not isinstance(summary, dict):
        raise ValueError("supervised dataset smoke summary must be a dict")

    _validate_key_set(
        "supervised dataset smoke summary",
        actual_keys=summary.keys(),
        expected_keys=SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS,
    )

    _validate_supervised_split_count_mapping(
        summary,
        "split_counts_before_label_drop",
    )
    _validate_supervised_split_count_mapping(
        summary,
        "split_counts_after_label_drop",
    )
    _validate_supervised_split_count_mapping(summary, "dropped_label_counts")

    split_shape = summary["split_shape"]
    if not isinstance(split_shape, dict):
        raise ValueError("supervised dataset smoke summary split_shape must be a dict")
    _validate_key_set(
        "supervised dataset smoke summary split_shape",
        actual_keys=split_shape.keys(),
        expected_keys=SUPERVISED_DATASET_SMOKE_SPLITS,
    )

    for split_name in sorted(SUPERVISED_DATASET_SMOKE_SPLITS):
        shape = split_shape[split_name]
        if not isinstance(shape, dict):
            raise ValueError(f"split_shape for {split_name} must be a dict")
        _validate_key_set(
            f"split_shape for {split_name}",
            actual_keys=shape.keys(),
            expected_keys=SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS,
        )

    return summary


def _validate_supervised_split_count_mapping(
    summary: dict[str, Any],
    key: str,
) -> None:
    split_counts = summary[key]
    if not isinstance(split_counts, dict):
        raise ValueError(f"supervised dataset smoke summary {key} must be a dict")
    _validate_key_set(
        f"supervised dataset smoke summary {key}",
        actual_keys=split_counts.keys(),
        expected_keys=SUPERVISED_DATASET_SMOKE_SPLITS,
    )


def _validate_linear_regression_split_mapping(
    summary: dict[str, Any],
    key: str,
) -> None:
    split_counts = summary[key]
    if not isinstance(split_counts, dict):
        raise ValueError(f"linear regression smoke summary {key} must be a dict")
    _validate_key_set(
        f"linear regression smoke summary {key}",
        actual_keys=split_counts.keys(),
        expected_keys=LINEAR_REGRESSION_SMOKE_SPLITS,
    )


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
