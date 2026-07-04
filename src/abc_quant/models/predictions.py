"""Prediction bundle contracts shared by diagnostic model workflows."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from abc_quant.models.baseline import ConstantBaselineResult


@dataclass(frozen=True)
class SplitPredictionBundle:
    """Train/validation/test prediction Series grouped by model metadata."""

    model_name: str
    method: str | None
    train_predictions: pd.Series
    validation_predictions: pd.Series
    test_predictions: pd.Series


def build_split_prediction_bundle(
    *,
    model_name: str,
    train_predictions: pd.Series,
    validation_predictions: pd.Series,
    test_predictions: pd.Series,
    method: str | None = None,
) -> SplitPredictionBundle:
    """Build a validated train/validation/test prediction bundle.

    This contract validates in-memory prediction outputs only. It does not
    implement estimators, fit preprocessing, tune parameters, create allocation
    logic, build performance curves, or run simulation engines.
    """
    normalized_model_name = _normalize_required_text(model_name, "model_name")
    normalized_method = (
        None if method is None else _normalize_required_text(method, "method")
    )
    copied_train = _validate_prediction_series(
        train_predictions,
        split_name="train",
        require_non_empty=True,
    )
    copied_validation = _validate_prediction_series(
        validation_predictions,
        split_name="validation",
        require_non_empty=False,
    )
    copied_test = _validate_prediction_series(
        test_predictions,
        split_name="test",
        require_non_empty=True,
    )
    _validate_disjoint_indices(
        train=copied_train,
        validation=copied_validation,
        test=copied_test,
    )

    return SplitPredictionBundle(
        model_name=normalized_model_name,
        method=normalized_method,
        train_predictions=copied_train,
        validation_predictions=copied_validation,
        test_predictions=copied_test,
    )


def build_constant_baseline_prediction_bundle(
    baseline_result: ConstantBaselineResult,
    model_name: str = "constant_baseline",
) -> SplitPredictionBundle:
    """Adapt a constant-baseline result to the generic prediction bundle."""
    if not isinstance(baseline_result, ConstantBaselineResult):
        raise TypeError("baseline_result must be a ConstantBaselineResult")
    return build_split_prediction_bundle(
        model_name=model_name,
        method=baseline_result.method,
        train_predictions=baseline_result.train_predictions,
        validation_predictions=baseline_result.validation_predictions,
        test_predictions=baseline_result.test_predictions,
    )


def _normalize_required_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _validate_prediction_series(
    series: pd.Series,
    *,
    split_name: str,
    require_non_empty: bool,
) -> pd.Series:
    if not isinstance(series, pd.Series):
        raise TypeError(f"{split_name}_predictions must be a pandas Series")
    if require_non_empty and series.empty:
        raise ValueError(f"{split_name}_predictions must not be empty")
    if series.index.has_duplicates:
        raise ValueError(f"{split_name}_predictions index must be unique")
    if series.isna().any():
        raise ValueError(f"{split_name}_predictions must not contain missing values")
    return series.copy(deep=True)


def _validate_disjoint_indices(**splits: pd.Series) -> None:
    split_names = sorted(splits)
    for left_position, left_name in enumerate(split_names):
        left_index = splits[left_name].index
        for right_name in split_names[left_position + 1 :]:
            overlap = left_index.intersection(splits[right_name].index)
            if len(overlap) > 0:
                examples = ", ".join(repr(value) for value in overlap[:5].tolist())
                raise ValueError(
                    "prediction indices must not overlap across splits: "
                    f"{left_name}/{right_name} overlap includes {examples}"
                )
