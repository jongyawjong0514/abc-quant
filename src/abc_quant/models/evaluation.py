"""Prediction evaluation contracts for model outputs."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import pandas as pd

from abc_quant.features.matrix import FeatureMatrix
from abc_quant.models.baseline import ConstantBaselineResult
from abc_quant.models.predictions import SplitPredictionBundle


@dataclass(frozen=True)
class PredictionEvaluationResult:
    """Error diagnostics for one evaluated prediction split."""

    split_name: str
    row_count: int
    non_missing_count: int
    missing_actual_count: int
    mae: float
    rmse: float
    mean_error: float
    prediction_mean: float


@dataclass(frozen=True)
class ConstantBaselineEvaluationResult:
    """Train/validation/test diagnostics for a constant baseline result."""

    train: PredictionEvaluationResult
    validation: PredictionEvaluationResult
    test: PredictionEvaluationResult


@dataclass(frozen=True)
class SplitPredictionBundleEvaluationResult:
    """Train/validation/test diagnostics for a split prediction bundle."""

    model_name: str
    method: str | None
    train: PredictionEvaluationResult
    validation: PredictionEvaluationResult
    test: PredictionEvaluationResult


def evaluate_predictions(
    actual: pd.Series,
    prediction: pd.Series,
    split_name: str,
) -> PredictionEvaluationResult:
    """Evaluate aligned predictions against actual labels.

    Missing actual labels are counted but excluded from error metrics. The
    prediction index defines the evaluated split and must be present in the
    actual-label index. This function does not create trading signals,
    positions, equity curves, strategy logic, or backtest outputs.
    """
    actual_series = _require_series(actual, "actual")
    prediction_series = _require_series(prediction, "prediction")
    normalized_split_name = _normalize_split_name(split_name)

    if prediction_series.empty:
        raise ValueError("prediction must not be empty")
    _validate_unique_index(actual_series, "actual")
    _validate_unique_index(prediction_series, "prediction")
    _validate_prediction_index(actual_series, prediction_series)

    aligned_actual = actual_series.reindex(prediction_series.index)
    numeric_prediction = _coerce_numeric(prediction_series, "prediction values")
    if numeric_prediction.isna().any():
        raise ValueError("prediction values must not contain missing values")

    non_missing_mask = aligned_actual.notna()
    non_missing_count = int(non_missing_mask.sum())
    if non_missing_count == 0:
        raise ValueError(
            f"no non-missing actual labels remain for split: {normalized_split_name}"
        )

    numeric_actual = _coerce_numeric(
        aligned_actual.loc[non_missing_mask],
        "actual labels",
    ).astype("float64")
    numeric_prediction_for_errors = numeric_prediction.loc[non_missing_mask].astype(
        "float64"
    )
    errors = numeric_prediction_for_errors - numeric_actual

    row_count = int(len(prediction_series))
    return PredictionEvaluationResult(
        split_name=normalized_split_name,
        row_count=row_count,
        non_missing_count=non_missing_count,
        missing_actual_count=row_count - non_missing_count,
        mae=float(errors.abs().mean()),
        rmse=float(sqrt(float((errors**2).mean()))),
        mean_error=float(errors.mean()),
        prediction_mean=float(numeric_prediction.astype("float64").mean()),
    )


def evaluate_prediction_bundle(
    feature_matrix: FeatureMatrix,
    prediction_bundle: SplitPredictionBundle,
) -> SplitPredictionBundleEvaluationResult:
    """Evaluate train/validation/test predictions from a prediction bundle."""
    if not isinstance(feature_matrix, FeatureMatrix):
        raise TypeError("feature_matrix must be a FeatureMatrix")
    if not isinstance(prediction_bundle, SplitPredictionBundle):
        raise TypeError("prediction_bundle must be a SplitPredictionBundle")

    return SplitPredictionBundleEvaluationResult(
        model_name=prediction_bundle.model_name,
        method=prediction_bundle.method,
        train=evaluate_predictions(
            feature_matrix.y,
            prediction_bundle.train_predictions,
            "train",
        ),
        validation=evaluate_predictions(
            feature_matrix.y,
            prediction_bundle.validation_predictions,
            "validation",
        ),
        test=evaluate_predictions(
            feature_matrix.y,
            prediction_bundle.test_predictions,
            "test",
        ),
    )


def evaluate_constant_baseline(
    feature_matrix: FeatureMatrix,
    baseline_result: ConstantBaselineResult,
) -> ConstantBaselineEvaluationResult:
    """Evaluate train/validation/test predictions from a constant baseline."""
    if not isinstance(feature_matrix, FeatureMatrix):
        raise TypeError("feature_matrix must be a FeatureMatrix")
    if not isinstance(baseline_result, ConstantBaselineResult):
        raise TypeError("baseline_result must be a ConstantBaselineResult")

    return ConstantBaselineEvaluationResult(
        train=evaluate_predictions(
            feature_matrix.y,
            baseline_result.train_predictions,
            "train",
        ),
        validation=evaluate_predictions(
            feature_matrix.y,
            baseline_result.validation_predictions,
            "validation",
        ),
        test=evaluate_predictions(
            feature_matrix.y,
            baseline_result.test_predictions,
            "test",
        ),
    )


def _require_series(value: pd.Series, name: str) -> pd.Series:
    if not isinstance(value, pd.Series):
        raise TypeError(f"{name} must be a pandas Series")
    return value


def _normalize_split_name(split_name: str) -> str:
    if not isinstance(split_name, str) or not split_name.strip():
        raise ValueError("split_name must not be empty")
    return split_name.strip()


def _validate_unique_index(series: pd.Series, name: str) -> None:
    if series.index.has_duplicates:
        raise ValueError(f"{name} index must not contain duplicates")


def _validate_prediction_index(actual: pd.Series, prediction: pd.Series) -> None:
    missing_index = prediction.index[~prediction.index.isin(actual.index)]
    if len(missing_index) > 0:
        examples = ", ".join(repr(value) for value in missing_index[:5].tolist())
        raise ValueError(
            "prediction index contains labels not present in actual labels: "
            + examples
        )


def _coerce_numeric(series: pd.Series, name: str) -> pd.Series:
    try:
        return pd.to_numeric(series, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
