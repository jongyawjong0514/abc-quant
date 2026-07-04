"""Train-only feature scaling contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd
from pandas.api.types import is_numeric_dtype

from abc_quant.features.matrix import FeatureMatrix
from abc_quant.validation.temporal import TemporalSplit


@dataclass(frozen=True)
class StandardScalerFit:
    """Feature means/stds fitted only from the train split."""

    feature_columns: tuple[str, ...]
    means: pd.Series
    stds: pd.Series
    train_index: tuple[int, ...]
    validation_index: tuple[int, ...]
    test_index: tuple[int, ...]


@dataclass(frozen=True)
class StandardizedFeatureMatrix:
    """Standardized train/validation/test feature frames and fitted parameters."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    fitted: StandardScalerFit


def fit_standard_scaler(
    feature_matrix: FeatureMatrix,
    temporal_split: TemporalSplit,
    feature_columns: Sequence[str] | None = None,
) -> StandardScalerFit:
    """Fit feature means and population stds using training rows only."""
    if not isinstance(feature_matrix, FeatureMatrix):
        raise TypeError("feature_matrix must be a FeatureMatrix")
    if not isinstance(temporal_split, TemporalSplit):
        raise TypeError("temporal_split must be a TemporalSplit")

    selected_features = _validate_feature_columns(feature_matrix, feature_columns)
    _validate_split_positions(feature_matrix, temporal_split)
    if not temporal_split.train_index:
        raise ValueError("standard scaler requires a non-empty train split")

    train_frame = _split_features(
        feature_matrix.X,
        temporal_split.train_index,
        selected_features,
    )
    missing_train_columns = [
        column for column in selected_features if train_frame[column].isna().any()
    ]
    if missing_train_columns:
        raise ValueError(
            "standard scaler training features contain missing values: "
            + ", ".join(missing_train_columns)
        )

    numeric_train = train_frame.astype("float64")
    means = numeric_train.mean(axis=0)
    stds = numeric_train.std(axis=0, ddof=0)
    zero_variance_columns = [
        column for column in selected_features if float(stds.loc[column]) == 0.0
    ]
    if zero_variance_columns:
        raise ValueError(
            "standard scaler training features have zero variance: "
            + ", ".join(zero_variance_columns)
        )

    return StandardScalerFit(
        feature_columns=selected_features,
        means=means.copy(deep=True),
        stds=stds.copy(deep=True),
        train_index=tuple(temporal_split.train_index),
        validation_index=tuple(temporal_split.validation_index),
        test_index=tuple(temporal_split.test_index),
    )


def transform_with_standard_scaler(
    feature_matrix: FeatureMatrix,
    fitted_scaler: StandardScalerFit,
    temporal_split: TemporalSplit,
) -> StandardizedFeatureMatrix:
    """Apply fitted train-only scaling parameters to train/validation/test rows."""
    if not isinstance(feature_matrix, FeatureMatrix):
        raise TypeError("feature_matrix must be a FeatureMatrix")
    if not isinstance(fitted_scaler, StandardScalerFit):
        raise TypeError("fitted_scaler must be a StandardScalerFit")
    if not isinstance(temporal_split, TemporalSplit):
        raise TypeError("temporal_split must be a TemporalSplit")

    _validate_fitted_scaler(fitted_scaler)
    _validate_feature_columns(feature_matrix, fitted_scaler.feature_columns)
    _validate_split_positions(feature_matrix, temporal_split)
    _validate_matching_split(fitted_scaler, temporal_split)

    return StandardizedFeatureMatrix(
        train=_transform_split(feature_matrix.X, fitted_scaler, temporal_split.train_index),
        validation=_transform_split(
            feature_matrix.X,
            fitted_scaler,
            temporal_split.validation_index,
        ),
        test=_transform_split(feature_matrix.X, fitted_scaler, temporal_split.test_index),
        fitted=fitted_scaler,
    )


def _validate_feature_columns(
    feature_matrix: FeatureMatrix,
    feature_columns: Sequence[str] | None,
) -> tuple[str, ...]:
    selected_features = (
        tuple(feature_matrix.feature_columns)
        if feature_columns is None
        else tuple(str(column) for column in feature_columns)
    )
    if not selected_features:
        raise ValueError("standard scaler feature_columns must not be empty")

    duplicates = sorted(
        {column for column in selected_features if selected_features.count(column) > 1}
    )
    if duplicates:
        raise ValueError(
            "standard scaler feature_columns contains duplicates: "
            + ", ".join(duplicates)
        )

    unknown = [column for column in selected_features if column not in feature_matrix.X]
    if unknown:
        raise ValueError(
            "standard scaler feature_columns are unknown: " + ", ".join(unknown)
        )

    nonnumeric = [
        column
        for column in selected_features
        if not is_numeric_dtype(feature_matrix.X[column])
    ]
    if nonnumeric:
        raise ValueError(
            "standard scaler feature_columns must be numeric: " + ", ".join(nonnumeric)
        )
    return selected_features


def _validate_split_positions(
    feature_matrix: FeatureMatrix,
    temporal_split: TemporalSplit,
) -> None:
    row_count = len(feature_matrix.X)
    positions = (
        *temporal_split.train_index,
        *temporal_split.validation_index,
        *temporal_split.test_index,
    )
    invalid_positions = [
        position for position in positions if position < 0 or position >= row_count
    ]
    if invalid_positions:
        raise ValueError(
            "temporal split contains positions outside the feature matrix: "
            + ", ".join(str(position) for position in invalid_positions[:5])
        )


def _validate_fitted_scaler(fitted_scaler: StandardScalerFit) -> None:
    if not fitted_scaler.feature_columns:
        raise ValueError("fitted scaler feature_columns must not be empty")
    if not fitted_scaler.means.index.equals(pd.Index(fitted_scaler.feature_columns)):
        raise ValueError("fitted scaler means index must match feature_columns")
    if not fitted_scaler.stds.index.equals(pd.Index(fitted_scaler.feature_columns)):
        raise ValueError("fitted scaler stds index must match feature_columns")
    if fitted_scaler.means.isna().any():
        raise ValueError("fitted scaler means must not contain missing values")
    if fitted_scaler.stds.isna().any():
        raise ValueError("fitted scaler stds must not contain missing values")
    zero_or_negative = [
        column
        for column in fitted_scaler.feature_columns
        if float(fitted_scaler.stds.loc[column]) <= 0.0
    ]
    if zero_or_negative:
        raise ValueError(
            "fitted scaler stds must be positive: " + ", ".join(zero_or_negative)
        )


def _validate_matching_split(
    fitted_scaler: StandardScalerFit,
    temporal_split: TemporalSplit,
) -> None:
    if fitted_scaler.train_index != tuple(temporal_split.train_index):
        raise ValueError("fitted scaler train_index must match temporal_split")
    if fitted_scaler.validation_index != tuple(temporal_split.validation_index):
        raise ValueError("fitted scaler validation_index must match temporal_split")
    if fitted_scaler.test_index != tuple(temporal_split.test_index):
        raise ValueError("fitted scaler test_index must match temporal_split")


def _split_features(
    features: pd.DataFrame,
    positions: tuple[int, ...],
    feature_columns: tuple[str, ...],
) -> pd.DataFrame:
    return features.iloc[list(positions)].loc[:, list(feature_columns)].copy()


def _transform_split(
    features: pd.DataFrame,
    fitted_scaler: StandardScalerFit,
    positions: tuple[int, ...],
) -> pd.DataFrame:
    split = _split_features(features, positions, fitted_scaler.feature_columns)
    standardized = (split.astype("float64") - fitted_scaler.means) / fitted_scaler.stds
    standardized.index = pd.Index(positions, dtype="int64")
    return standardized
