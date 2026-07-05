"""Deterministic baseline-versus-OLS comparison smoke diagnostics."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Final

import pandas as pd

from abc_quant.features.matrix import FeatureMatrix, build_feature_matrix
from abc_quant.models.baseline import ConstantBaselineMethod, fit_constant_baseline
from abc_quant.models.comparison import compare_prediction_evaluations
from abc_quant.models.dataset import SupervisedSplitDataset, build_supervised_split_dataset
from abc_quant.models.evaluation import evaluate_prediction_bundle
from abc_quant.models.linear import fit_linear_regression
from abc_quant.models.predictions import build_split_prediction_bundle
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
from abc_quant.validation.temporal import TemporalSplit, build_temporal_split

DEFAULT_MODEL_COMPARISON_TRAIN_END: Final[str] = DEFAULT_SUPERVISED_DATASET_TRAIN_END
DEFAULT_MODEL_COMPARISON_VALIDATION_END: Final[str] = (
    DEFAULT_SUPERVISED_DATASET_VALIDATION_END
)
DEFAULT_MODEL_COMPARISON_BASELINE_METHOD: Final[ConstantBaselineMethod] = "mean"


def run_model_comparison_smoke(
    *,
    train_end: str = DEFAULT_MODEL_COMPARISON_TRAIN_END,
    validation_end: str = DEFAULT_MODEL_COMPARISON_VALIDATION_END,
    baseline_method: ConstantBaselineMethod = DEFAULT_MODEL_COMPARISON_BASELINE_METHOD,
) -> dict[str, Any]:
    """Run deterministic constant-baseline versus OLS comparison diagnostics.

    This wires existing in-memory contracts together and returns only
    JSON-friendly diagnostic values. It does not select a model, rank models,
    create strategy signals, define allocation logic, build performance curves,
    or run simulation engines.
    """
    feature_matrix, temporal_split, supervised_dataset = _comparison_inputs(
        train_end=train_end,
        validation_end=validation_end,
    )

    baseline = fit_constant_baseline(
        feature_matrix,
        temporal_split,
        method=baseline_method,
    )
    reference_bundle = build_split_prediction_bundle(
        model_name="constant_baseline",
        method=baseline.method,
        train_predictions=_subset_predictions(
            baseline.train_predictions,
            supervised_dataset.train_X.index,
        ),
        validation_predictions=_subset_predictions(
            baseline.validation_predictions,
            supervised_dataset.validation_X.index,
        ),
        test_predictions=_subset_predictions(
            baseline.test_predictions,
            supervised_dataset.test_X.index,
        ),
    )
    linear_result = fit_linear_regression(supervised_dataset)

    reference_evaluation = evaluate_prediction_bundle(feature_matrix, reference_bundle)
    candidate_evaluation = evaluate_prediction_bundle(
        feature_matrix,
        linear_result.prediction_bundle,
    )
    comparison = compare_prediction_evaluations(
        reference_evaluation,
        candidate_evaluation,
        reference_name=reference_evaluation.model_name,
        candidate_name=candidate_evaluation.model_name,
    )

    return {
        "row_count": int(len(feature_matrix.X)),
        "feature_columns": list(supervised_dataset.feature_columns),
        "label_column": supervised_dataset.label_column,
        "reference_model": {
            "model_name": reference_evaluation.model_name,
            "method": reference_evaluation.method,
        },
        "candidate_model": {
            "model_name": candidate_evaluation.model_name,
            "method": candidate_evaluation.method,
        },
        "split_counts": _dataset_split_counts(supervised_dataset),
        "dropped_label_counts": {
            split_name: int(count)
            for split_name, count in supervised_dataset.dropped_label_counts.items()
        },
        "reference_evaluation": asdict(reference_evaluation),
        "candidate_evaluation": asdict(candidate_evaluation),
        "comparison": asdict(comparison),
    }


def _comparison_inputs(
    *,
    train_end: str,
    validation_end: str,
) -> tuple[FeatureMatrix, TemporalSplit, SupervisedSplitDataset]:
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
    return feature_matrix, temporal_split, supervised_dataset


def _feature_complete_smoke_frame() -> pd.DataFrame:
    frame = build_smoke_frame()
    return frame.dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(drop=True)


def _subset_predictions(predictions: pd.Series, index: pd.Index) -> pd.Series:
    return predictions.reindex(index).copy(deep=True)


def _dataset_split_counts(dataset: SupervisedSplitDataset) -> dict[str, int]:
    return {
        "train": int(len(dataset.train_X)),
        "validation": int(len(dataset.validation_X)),
        "test": int(len(dataset.test_X)),
    }
