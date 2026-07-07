"""Optional LightGBM evaluation smoke diagnostics."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Final

import pandas as pd

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.dataset import build_supervised_split_dataset
from abc_quant.models.evaluation import (
    PredictionEvaluationResult,
    SplitPredictionBundleEvaluationResult,
    evaluate_prediction_bundle,
)
from abc_quant.models.lightgbm import (
    LightGBMDependencyStatus,
    check_lightgbm_dependency,
    fit_lightgbm_regressor,
    make_default_lightgbm_regressor_params,
)
from abc_quant.pipeline.contracts import EVALUATION_METRIC_KEYS
from abc_quant.pipeline.lightgbm_diagnostics import (
    LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS,
    LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS,
)
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)
from abc_quant.pipeline.supervised import (
    DEFAULT_SUPERVISED_DATASET_TRAIN_END,
    DEFAULT_SUPERVISED_DATASET_VALIDATION_END,
)
from abc_quant.preprocessing.scaling import (
    fit_standard_scaler,
    transform_with_standard_scaler,
)
from abc_quant.validation.temporal import build_temporal_split

DEFAULT_LIGHTGBM_EVALUATION_TRAIN_END: Final[str] = (
    DEFAULT_SUPERVISED_DATASET_TRAIN_END
)
DEFAULT_LIGHTGBM_EVALUATION_VALIDATION_END: Final[str] = (
    DEFAULT_SUPERVISED_DATASET_VALIDATION_END
)
LIGHTGBM_EVALUATION_SMOKE_SUMMARY_KEYS: Final[tuple[str, ...]] = (
    "package_name",
    "installed",
    "message",
    "default_params",
    "fitting_enabled",
    "fitted",
    "unavailable_reason",
    "model_name",
    "method",
    "feature_columns",
    "training_row_count",
    "evaluation",
)
LIGHTGBM_EVALUATION_SMOKE_DEFAULT_PARAM_KEYS: Final[tuple[str, ...]] = (
    LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS
)
LIGHTGBM_EVALUATION_SMOKE_SPLITS: Final[frozenset[str]] = frozenset(
    {"train", "validation", "test"}
)
LIGHTGBM_EVALUATION_SMOKE_EVALUATION_KEYS: Final[frozenset[str]] = (
    EVALUATION_METRIC_KEYS
)
LIGHTGBM_EVALUATION_SMOKE_FORBIDDEN_KEYS: Final[tuple[str, ...]] = (
    LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS
)


def run_lightgbm_evaluation_smoke(
    *,
    fitting_enabled: bool = False,
) -> dict[str, Any]:
    """Return JSON-friendly optional LightGBM evaluation diagnostics.

    The default path checks dependency status and default parameters only. It
    does not call `require_lightgbm()` or fit a model. Opt-in fitting uses the
    existing train-only LightGBM contract and deterministic in-memory smoke
    data.
    """
    dependency_status = check_lightgbm_dependency()
    default_params = make_default_lightgbm_regressor_params()
    if not fitting_enabled:
        return validate_lightgbm_evaluation_smoke_summary(
            _base_summary(
                dependency_status,
                default_params=asdict(default_params),
                fitting_enabled=False,
            )
        )
    if not dependency_status.installed:
        return validate_lightgbm_evaluation_smoke_summary(
            _base_summary(
                dependency_status,
                default_params=asdict(default_params),
                fitting_enabled=True,
                unavailable_reason=dependency_status.message,
            )
        )

    feature_matrix, supervised_dataset = _supervised_smoke_dataset()
    lightgbm_result = fit_lightgbm_regressor(
        supervised_dataset,
        params=default_params,
    )
    evaluation = evaluate_prediction_bundle(
        feature_matrix,
        lightgbm_result.prediction_bundle,
    )

    summary = _base_summary(
        dependency_status,
        default_params=asdict(lightgbm_result.params),
        fitting_enabled=True,
    )
    summary.update(
        {
            "fitted": True,
            "model_name": lightgbm_result.model_name,
            "method": lightgbm_result.method,
            "feature_columns": list(lightgbm_result.feature_columns),
            "training_row_count": int(lightgbm_result.training_row_count),
            "evaluation": _evaluation_summary(evaluation),
        }
    )
    return validate_lightgbm_evaluation_smoke_summary(summary)


def validate_lightgbm_evaluation_smoke_summary(
    summary: object,
) -> dict[str, Any]:
    """Validate the LightGBM evaluation smoke diagnostics summary shape."""
    if not isinstance(summary, dict):
        raise TypeError("LightGBM evaluation smoke summary must be a dict")

    forbidden = sorted(
        set(LIGHTGBM_EVALUATION_SMOKE_FORBIDDEN_KEYS) & _collect_nested_keys(summary)
    )
    if forbidden:
        raise ValueError(
            "LightGBM evaluation smoke summary contains forbidden keys: "
            + ", ".join(forbidden)
        )

    _validate_key_tuple(
        "LightGBM evaluation smoke summary",
        actual_keys=summary.keys(),
        expected_keys=LIGHTGBM_EVALUATION_SMOKE_SUMMARY_KEYS,
    )
    _validate_default_params(summary)
    _validate_evaluation(summary)

    try:
        json.dumps(summary, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "LightGBM evaluation smoke summary must be JSON-friendly"
        ) from exc

    return summary


def _base_summary(
    dependency_status: LightGBMDependencyStatus,
    *,
    default_params: dict[str, Any],
    fitting_enabled: bool,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "package_name": dependency_status.package_name,
        "installed": bool(dependency_status.installed),
        "message": dependency_status.message,
        "default_params": default_params,
        "fitting_enabled": bool(fitting_enabled),
        "fitted": False,
        "unavailable_reason": unavailable_reason,
        "model_name": None,
        "method": None,
        "feature_columns": [],
        "training_row_count": 0,
        "evaluation": None,
    }


def _supervised_smoke_dataset():
    frame = _feature_complete_smoke_frame()
    feature_matrix = build_feature_matrix(
        frame,
        SMOKE_LABEL_COLUMN,
        feature_columns=SMOKE_FEATURE_COLUMNS,
    )
    temporal_split = build_temporal_split(
        feature_matrix.metadata,
        train_end=DEFAULT_LIGHTGBM_EVALUATION_TRAIN_END,
        validation_end=DEFAULT_LIGHTGBM_EVALUATION_VALIDATION_END,
    )
    fitted_scaler = fit_standard_scaler(feature_matrix, temporal_split)
    standardized = transform_with_standard_scaler(
        feature_matrix,
        fitted_scaler,
        temporal_split,
    )
    supervised_dataset = build_supervised_split_dataset(
        feature_matrix,
        standardized,
        drop_missing_labels=True,
    )
    return feature_matrix, supervised_dataset


def _feature_complete_smoke_frame() -> pd.DataFrame:
    frame = build_smoke_frame()
    return frame.dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(drop=True)


def _evaluation_summary(
    evaluation: SplitPredictionBundleEvaluationResult,
) -> dict[str, dict[str, object]]:
    return {
        "train": _prediction_evaluation_summary(evaluation.train),
        "validation": _prediction_evaluation_summary(evaluation.validation),
        "test": _prediction_evaluation_summary(evaluation.test),
    }


def _prediction_evaluation_summary(
    result: PredictionEvaluationResult,
) -> dict[str, object]:
    return asdict(result)


def _validate_default_params(summary: dict[str, Any]) -> None:
    default_params = summary["default_params"]
    if not isinstance(default_params, dict):
        raise ValueError(
            "LightGBM evaluation smoke summary default_params must be a dict"
        )
    _validate_key_tuple(
        "LightGBM evaluation smoke summary default_params",
        actual_keys=default_params.keys(),
        expected_keys=LIGHTGBM_EVALUATION_SMOKE_DEFAULT_PARAM_KEYS,
    )


def _validate_evaluation(summary: dict[str, Any]) -> None:
    evaluation = summary["evaluation"]
    if evaluation is None:
        return
    if not isinstance(evaluation, dict):
        raise ValueError("LightGBM evaluation smoke summary evaluation must be a dict")
    _validate_key_set(
        "LightGBM evaluation smoke summary evaluation",
        actual_keys=evaluation.keys(),
        expected_keys=LIGHTGBM_EVALUATION_SMOKE_SPLITS,
    )
    for split_name in sorted(LIGHTGBM_EVALUATION_SMOKE_SPLITS):
        metrics = evaluation[split_name]
        if not isinstance(metrics, dict):
            raise ValueError(f"LightGBM metrics for {split_name} must be a dict")
        _validate_key_set(
            f"LightGBM metrics for {split_name}",
            actual_keys=metrics.keys(),
            expected_keys=LIGHTGBM_EVALUATION_SMOKE_EVALUATION_KEYS,
        )


def _validate_key_tuple(
    context: str,
    *,
    actual_keys: object,
    expected_keys: tuple[str, ...],
) -> None:
    expected = set(expected_keys)
    actual = {str(key) for key in actual_keys}
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{context} keys mismatch: missing={missing}; unknown={unknown}"
        )


def _validate_key_set(
    context: str,
    *,
    actual_keys: object,
    expected_keys: frozenset[str],
) -> None:
    expected = set(expected_keys)
    actual = {str(key) for key in actual_keys}
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{context} keys mismatch: missing={missing}; unknown={unknown}"
        )


def _collect_nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_collect_nested_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_nested_keys(item))
        return keys
    return set()
