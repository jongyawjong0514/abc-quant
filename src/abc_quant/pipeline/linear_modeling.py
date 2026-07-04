"""Deterministic train-only OLS smoke diagnostics."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Final

import pandas as pd

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.dataset import SupervisedSplitDataset, build_supervised_split_dataset
from abc_quant.models.evaluation import (
    PredictionEvaluationResult,
    SplitPredictionBundleEvaluationResult,
    evaluate_prediction_bundle,
)
from abc_quant.models.linear import LinearRegressionResult, fit_linear_regression
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

DEFAULT_LINEAR_REGRESSION_TRAIN_END: Final[str] = DEFAULT_SUPERVISED_DATASET_TRAIN_END
DEFAULT_LINEAR_REGRESSION_VALIDATION_END: Final[str] = (
    DEFAULT_SUPERVISED_DATASET_VALIDATION_END
)


def run_linear_regression_smoke(
    *,
    train_end: str = DEFAULT_LINEAR_REGRESSION_TRAIN_END,
    validation_end: str = DEFAULT_LINEAR_REGRESSION_VALIDATION_END,
) -> dict[str, Any]:
    """Run deterministic train-only OLS diagnostics.

    This wires existing in-memory contracts together and returns only diagnostic
    scalar/list/dict values. It does not create strategy signals, allocation
    outputs, performance curves, or simulation results.
    """
    feature_matrix, supervised_dataset = _supervised_smoke_dataset(
        train_end=train_end,
        validation_end=validation_end,
    )
    linear_result = fit_linear_regression(supervised_dataset)
    evaluation = evaluate_prediction_bundle(
        feature_matrix,
        linear_result.prediction_bundle,
    )

    summary = {
        "row_count": int(len(feature_matrix.X)),
        "feature_columns": list(linear_result.feature_columns),
        "label_column": supervised_dataset.label_column,
        "model_name": linear_result.model_name,
        "method": linear_result.method,
        "intercept": float(linear_result.intercept),
        "coefficients": _series_to_float_dict(
            linear_result.coefficients,
            linear_result.feature_columns,
        ),
        "training_row_count": int(linear_result.training_row_count),
        "split_counts_after_label_drop": _dataset_split_counts(supervised_dataset),
        "dropped_label_counts": {
            split_name: int(count)
            for split_name, count in supervised_dataset.dropped_label_counts.items()
        },
        "prediction_counts": _prediction_counts(linear_result),
        "evaluation": _evaluation_summary(evaluation),
    }
    return summary


def _supervised_smoke_dataset(
    *,
    train_end: str,
    validation_end: str,
):
    frame = _feature_complete_smoke_frame()
    feature_matrix = build_feature_matrix(
        frame,
        SMOKE_LABEL_COLUMN,
        feature_columns=SMOKE_FEATURE_COLUMNS,
    )
    temporal_split = build_temporal_split(
        feature_matrix.metadata,
        train_end=train_end,
        validation_end=validation_end,
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


def _series_to_float_dict(
    series: pd.Series,
    feature_columns: tuple[str, ...],
) -> dict[str, float]:
    return {column: float(series.loc[column]) for column in feature_columns}


def _dataset_split_counts(dataset: SupervisedSplitDataset) -> dict[str, int]:
    return {
        "train": int(len(dataset.train_X)),
        "validation": int(len(dataset.validation_X)),
        "test": int(len(dataset.test_X)),
    }


def _prediction_counts(result: LinearRegressionResult) -> dict[str, int]:
    return {
        "train": int(len(result.prediction_bundle.train_predictions)),
        "validation": int(len(result.prediction_bundle.validation_predictions)),
        "test": int(len(result.prediction_bundle.test_predictions)),
    }


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
