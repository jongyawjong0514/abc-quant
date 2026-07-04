"""Supervised dataset contracts for split model inputs."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from abc_quant.features.matrix import FeatureMatrix
from abc_quant.preprocessing.scaling import StandardizedFeatureMatrix


@dataclass(frozen=True)
class SupervisedSplitDataset:
    """Train/validation/test supervised inputs with aligned labels."""

    feature_columns: tuple[str, ...]
    label_column: str
    train_X: pd.DataFrame
    train_y: pd.Series
    validation_X: pd.DataFrame
    validation_y: pd.Series
    test_X: pd.DataFrame
    test_y: pd.Series
    dropped_label_counts: dict[str, int]


def build_supervised_split_dataset(
    feature_matrix: FeatureMatrix,
    standardized_features: StandardizedFeatureMatrix,
    *,
    drop_missing_labels: bool = True,
) -> SupervisedSplitDataset:
    """Build aligned supervised train/validation/test inputs.

    This contract prepares already-standardized features and labels for future
    estimators. It does not train estimators, tune parameters, create allocation
    logic, build performance curves, or run simulation engines.
    """
    if not isinstance(feature_matrix, FeatureMatrix):
        raise TypeError("feature_matrix must be a FeatureMatrix")
    if not isinstance(standardized_features, StandardizedFeatureMatrix):
        raise TypeError("standardized_features must be a StandardizedFeatureMatrix")

    feature_columns = tuple(standardized_features.fitted.feature_columns)
    _validate_standardized_split(
        standardized_features.train,
        standardized_features.fitted.train_index,
        feature_columns,
        "train",
    )
    _validate_standardized_split(
        standardized_features.validation,
        standardized_features.fitted.validation_index,
        feature_columns,
        "validation",
    )
    _validate_standardized_split(
        standardized_features.test,
        standardized_features.fitted.test_index,
        feature_columns,
        "test",
    )

    train_X, train_y, train_dropped = _split_supervised_data(
        feature_matrix,
        standardized_features.train,
        "train",
        drop_missing_labels=drop_missing_labels,
    )
    validation_X, validation_y, validation_dropped = _split_supervised_data(
        feature_matrix,
        standardized_features.validation,
        "validation",
        drop_missing_labels=drop_missing_labels,
    )
    test_X, test_y, test_dropped = _split_supervised_data(
        feature_matrix,
        standardized_features.test,
        "test",
        drop_missing_labels=drop_missing_labels,
    )

    if train_X.empty:
        raise ValueError("supervised split dataset requires non-empty train data")

    return SupervisedSplitDataset(
        feature_columns=feature_columns,
        label_column=feature_matrix.label_column,
        train_X=train_X,
        train_y=train_y,
        validation_X=validation_X,
        validation_y=validation_y,
        test_X=test_X,
        test_y=test_y,
        dropped_label_counts={
            "train": train_dropped,
            "validation": validation_dropped,
            "test": test_dropped,
        },
    )


def _validate_standardized_split(
    features: pd.DataFrame,
    expected_index: tuple[int, ...],
    feature_columns: tuple[str, ...],
    split_name: str,
) -> None:
    if not features.index.equals(pd.Index(expected_index, dtype="int64")):
        raise ValueError(f"{split_name}_X index must match fitted {split_name}_index")
    if tuple(str(column) for column in features.columns) != feature_columns:
        raise ValueError(f"{split_name}_X columns must match fitted feature_columns")


def _split_supervised_data(
    feature_matrix: FeatureMatrix,
    features: pd.DataFrame,
    split_name: str,
    *,
    drop_missing_labels: bool,
) -> tuple[pd.DataFrame, pd.Series, int]:
    labels = _labels_for_split(feature_matrix, features.index, split_name)
    missing_mask = labels.isna()
    missing_count = int(missing_mask.sum())
    if missing_count and not drop_missing_labels:
        raise ValueError(f"{split_name} labels contain missing values")

    if drop_missing_labels and missing_count:
        keep_mask = ~missing_mask
        return (
            features.loc[keep_mask].copy(deep=True),
            labels.loc[keep_mask].copy(deep=True),
            missing_count,
        )

    return features.copy(deep=True), labels.copy(deep=True), missing_count


def _labels_for_split(
    feature_matrix: FeatureMatrix,
    index: pd.Index,
    split_name: str,
) -> pd.Series:
    positions = [int(position) for position in index.to_list()]
    invalid_positions = [
        position for position in positions if position < 0 or position >= len(feature_matrix.y)
    ]
    if invalid_positions:
        raise ValueError(
            f"{split_name}_X index contains positions outside feature_matrix labels: "
            + ", ".join(str(position) for position in invalid_positions[:5])
        )

    labels = feature_matrix.y.iloc[positions].copy(deep=True)
    labels.index = pd.Index(positions, dtype="int64")
    labels.name = feature_matrix.label_column
    return labels
