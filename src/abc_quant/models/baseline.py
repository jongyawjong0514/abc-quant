"""Minimal baseline model contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from abc_quant.features.matrix import FeatureMatrix
from abc_quant.validation.temporal import TemporalSplit

ConstantBaselineMethod = Literal["mean", "median"]


@dataclass(frozen=True)
class ConstantBaselineResult:
    """Constant predictions fitted only from non-missing training labels."""

    fitted_value: float
    train_predictions: pd.Series
    validation_predictions: pd.Series
    test_predictions: pd.Series
    training_label_count: int
    method: ConstantBaselineMethod


def fit_constant_baseline(
    feature_matrix: FeatureMatrix,
    temporal_split: TemporalSplit,
    method: ConstantBaselineMethod = "mean",
) -> ConstantBaselineResult:
    """Fit a mean or median constant baseline from training labels only.

    The returned prediction series are indexed by sorted matrix row positions.
    This helper does not fit scalers, tune parameters, train complex models,
    create trading signals, or run backtests.
    """
    if not isinstance(feature_matrix, FeatureMatrix):
        raise TypeError("feature_matrix must be a FeatureMatrix")
    if not isinstance(temporal_split, TemporalSplit):
        raise TypeError("temporal_split must be a TemporalSplit")

    normalized_method = _validate_method(method)
    _validate_split_positions(feature_matrix.y, temporal_split)
    if not temporal_split.train_index:
        raise ValueError("constant baseline requires a non-empty train split")

    train_labels = feature_matrix.y.iloc[list(temporal_split.train_index)].dropna()
    if train_labels.empty:
        raise ValueError("constant baseline requires at least one non-missing training label")

    numeric_train_labels = _coerce_numeric_train_labels(train_labels)
    fitted_value = (
        float(numeric_train_labels.mean())
        if normalized_method == "mean"
        else float(numeric_train_labels.median())
    )

    return ConstantBaselineResult(
        fitted_value=fitted_value,
        train_predictions=_constant_predictions(fitted_value, temporal_split.train_index),
        validation_predictions=_constant_predictions(
            fitted_value,
            temporal_split.validation_index,
        ),
        test_predictions=_constant_predictions(fitted_value, temporal_split.test_index),
        training_label_count=int(len(numeric_train_labels)),
        method=normalized_method,
    )


def _validate_method(method: str) -> ConstantBaselineMethod:
    if method == "mean" or method == "median":
        return method
    raise ValueError("constant baseline method must be one of: mean, median")


def _validate_split_positions(labels: pd.Series, temporal_split: TemporalSplit) -> None:
    label_count = len(labels)
    positions = (
        *temporal_split.train_index,
        *temporal_split.validation_index,
        *temporal_split.test_index,
    )
    invalid_positions = [
        position for position in positions if position < 0 or position >= label_count
    ]
    if invalid_positions:
        raise ValueError(
            "temporal split contains positions outside the feature matrix: "
            + ", ".join(str(position) for position in invalid_positions[:5])
        )


def _coerce_numeric_train_labels(labels: pd.Series) -> pd.Series:
    try:
        return pd.to_numeric(labels, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("training labels must be numeric") from exc


def _constant_predictions(value: float, positions: tuple[int, ...]) -> pd.Series:
    return pd.Series(
        value,
        index=pd.Index(positions, dtype="int64"),
        name="constant_baseline_prediction",
        dtype="float64",
    )
