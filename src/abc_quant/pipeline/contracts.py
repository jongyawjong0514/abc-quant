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

MODEL_COMPARISON_SMOKE_SUMMARY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "row_count",
        "feature_columns",
        "label_column",
        "reference_model",
        "candidate_model",
        "split_counts",
        "dropped_label_counts",
        "reference_evaluation",
        "candidate_evaluation",
        "comparison",
    }
)

MODEL_COMPARISON_SMOKE_SPLITS: Final[frozenset[str]] = frozenset(
    {"train", "validation", "test"}
)

MODEL_COMPARISON_SMOKE_MODEL_KEYS: Final[frozenset[str]] = frozenset(
    {"model_name", "method"}
)

MODEL_COMPARISON_SMOKE_COMPARISON_KEYS: Final[frozenset[str]] = frozenset(
    {"reference_name", "candidate_name", "train", "validation", "test"}
)

MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS: Final[frozenset[str]] = frozenset(
    {
        "split_name",
        "reference_name",
        "candidate_name",
        "row_count",
        "non_missing_count",
        "missing_actual_count",
        "mae_delta",
        "rmse_delta",
        "mean_error_delta",
        "prediction_mean_delta",
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


def validate_model_comparison_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the deterministic model-comparison smoke summary shape.

    The function returns the original summary object unchanged when valid.
    """
    if not isinstance(summary, dict):
        raise ValueError("model comparison smoke summary must be a dict")

    _validate_key_set(
        "model comparison smoke summary",
        actual_keys=summary.keys(),
        expected_keys=MODEL_COMPARISON_SMOKE_SUMMARY_KEYS,
    )

    _validate_model_comparison_model_metadata(summary, "reference_model")
    _validate_model_comparison_model_metadata(summary, "candidate_model")
    _validate_model_comparison_split_mapping(summary, "split_counts")
    _validate_model_comparison_split_mapping(summary, "dropped_label_counts")
    _validate_model_comparison_evaluation(summary, "reference_evaluation")
    _validate_model_comparison_evaluation(summary, "candidate_evaluation")
    _validate_model_comparison_comparison(summary)

    return summary


def _validate_model_comparison_model_metadata(
    summary: dict[str, Any],
    key: str,
) -> None:
    metadata = summary[key]
    if not isinstance(metadata, dict):
        raise ValueError(f"model comparison smoke summary {key} must be a dict")
    _validate_key_set(
        f"model comparison smoke summary {key}",
        actual_keys=metadata.keys(),
        expected_keys=MODEL_COMPARISON_SMOKE_MODEL_KEYS,
    )


def _validate_model_comparison_split_mapping(
    summary: dict[str, Any],
    key: str,
) -> None:
    split_mapping = summary[key]
    if not isinstance(split_mapping, dict):
        raise ValueError(f"model comparison smoke summary {key} must be a dict")
    _validate_key_set(
        f"model comparison smoke summary {key}",
        actual_keys=split_mapping.keys(),
        expected_keys=MODEL_COMPARISON_SMOKE_SPLITS,
    )


def _validate_model_comparison_evaluation(
    summary: dict[str, Any],
    key: str,
) -> None:
    evaluation = summary[key]
    if not isinstance(evaluation, dict):
        raise ValueError(f"model comparison smoke summary {key} must be a dict")
    _validate_key_set(
        f"model comparison smoke summary {key}",
        actual_keys=evaluation.keys(),
        expected_keys=MODEL_COMPARISON_SMOKE_MODEL_KEYS | MODEL_COMPARISON_SMOKE_SPLITS,
    )

    for split_name in sorted(MODEL_COMPARISON_SMOKE_SPLITS):
        metrics = evaluation[split_name]
        if not isinstance(metrics, dict):
            raise ValueError(f"{key} metrics for {split_name} must be a dict")
        _validate_key_set(
            f"{key} metrics for {split_name}",
            actual_keys=metrics.keys(),
            expected_keys=EVALUATION_METRIC_KEYS,
        )


def _validate_model_comparison_comparison(summary: dict[str, Any]) -> None:
    comparison = summary["comparison"]
    if not isinstance(comparison, dict):
        raise ValueError("model comparison smoke summary comparison must be a dict")
    _validate_key_set(
        "model comparison smoke summary comparison",
        actual_keys=comparison.keys(),
        expected_keys=MODEL_COMPARISON_SMOKE_COMPARISON_KEYS,
    )

    for split_name in sorted(MODEL_COMPARISON_SMOKE_SPLITS):
        split_comparison = comparison[split_name]
        if not isinstance(split_comparison, dict):
            raise ValueError(f"comparison for {split_name} must be a dict")
        _validate_key_set(
            f"comparison for {split_name}",
            actual_keys=split_comparison.keys(),
            expected_keys=MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS,
        )


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
