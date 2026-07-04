from dataclasses import replace

import pandas as pd
import pytest

from abc_quant.features.matrix import FeatureMatrix, build_feature_matrix
from abc_quant.models import (
    SupervisedSplitDataset,
    build_supervised_split_dataset,
)
from abc_quant.preprocessing.scaling import (
    StandardizedFeatureMatrix,
    fit_standard_scaler,
    transform_with_standard_scaler,
)
from abc_quant.validation.temporal import build_temporal_split


LABEL_COLUMN = "label_forward_return"


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=7, freq="D"),
            "ticker": ["2330"] * 7,
            "open": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0],
            "high": [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
            "low": [9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            "close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600],
            "feature_a": [1.0, 3.0, 5.0, 999.0, -999.0, 1500.0, -1500.0],
            "feature_b": [10.0, 14.0, 18.0, -500.0, 700.0, -900.0, 1100.0],
            LABEL_COLUMN: [0.01, pd.NA, 0.03, pd.NA, 0.05, 0.06, pd.NA],
        }
    )


def _matrix_and_standardized() -> tuple[FeatureMatrix, StandardizedFeatureMatrix]:
    matrix = build_feature_matrix(
        _frame(),
        LABEL_COLUMN,
        feature_columns=["feature_b", "feature_a"],
    )
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-03",
        validation_end="2026-01-05",
    )
    fitted = fit_standard_scaler(matrix, split, feature_columns=["feature_b", "feature_a"])
    standardized = transform_with_standard_scaler(matrix, fitted, split)
    return matrix, standardized


def test_build_supervised_split_dataset_accepts_valid_standardized_features() -> None:
    matrix, standardized = _matrix_and_standardized()

    dataset = build_supervised_split_dataset(matrix, standardized)

    assert isinstance(dataset, SupervisedSplitDataset)
    assert dataset.feature_columns == ("feature_b", "feature_a")
    assert dataset.label_column == LABEL_COLUMN
    assert tuple(dataset.train_X.index) == (0, 2)
    assert tuple(dataset.train_y.index) == (0, 2)
    assert tuple(dataset.validation_X.index) == (4,)
    assert tuple(dataset.validation_y.index) == (4,)
    assert tuple(dataset.test_X.index) == (5,)
    assert tuple(dataset.test_y.index) == (5,)
    assert dataset.dropped_label_counts == {"train": 1, "validation": 1, "test": 1}
    pd.testing.assert_series_equal(
        dataset.train_y,
        pd.Series([0.01, 0.03], index=pd.Index([0, 2], dtype="int64"), name=LABEL_COLUMN),
        check_dtype=False,
    )
    assert list(dataset.train_X.columns) == ["feature_b", "feature_a"]
    assert list(dataset.validation_X.columns) == ["feature_b", "feature_a"]
    assert list(dataset.test_X.columns) == ["feature_b", "feature_a"]


def test_build_supervised_split_dataset_can_keep_complete_labels() -> None:
    matrix, standardized = _matrix_and_standardized()
    complete_y = matrix.y.copy()
    complete_y.loc[:] = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
    complete_matrix = FeatureMatrix(
        X=matrix.X,
        y=complete_y,
        metadata=matrix.metadata,
        feature_columns=matrix.feature_columns,
        label_column=matrix.label_column,
    )

    dataset = build_supervised_split_dataset(
        complete_matrix,
        standardized,
        drop_missing_labels=False,
    )

    assert tuple(dataset.train_X.index) == (0, 1, 2)
    assert tuple(dataset.validation_X.index) == (3, 4)
    assert tuple(dataset.test_X.index) == (5, 6)
    assert dataset.dropped_label_counts == {"train": 0, "validation": 0, "test": 0}


def test_build_supervised_split_dataset_rejects_missing_labels_when_not_dropping() -> None:
    matrix, standardized = _matrix_and_standardized()

    with pytest.raises(ValueError, match="train labels contain missing values"):
        build_supervised_split_dataset(
            matrix,
            standardized,
            drop_missing_labels=False,
        )


def test_build_supervised_split_dataset_rejects_empty_train_after_filtering() -> None:
    matrix, standardized = _matrix_and_standardized()
    missing_train_y = matrix.y.copy()
    missing_train_y.iloc[list(standardized.fitted.train_index)] = pd.NA
    missing_train_matrix = FeatureMatrix(
        X=matrix.X,
        y=missing_train_y,
        metadata=matrix.metadata,
        feature_columns=matrix.feature_columns,
        label_column=matrix.label_column,
    )

    with pytest.raises(ValueError, match="non-empty train data"):
        build_supervised_split_dataset(missing_train_matrix, standardized)


def test_build_supervised_split_dataset_returns_copied_objects() -> None:
    matrix, standardized = _matrix_and_standardized()

    dataset = build_supervised_split_dataset(matrix, standardized)
    standardized.train.loc[0, "feature_b"] = 999.0
    standardized.validation.loc[4, "feature_a"] = 888.0
    standardized.test.loc[5, "feature_b"] = 777.0
    matrix.y.iloc[0] = 666.0

    assert dataset.train_X.loc[0, "feature_b"] != 999.0
    assert dataset.validation_X.loc[4, "feature_a"] != 888.0
    assert dataset.test_X.loc[5, "feature_b"] != 777.0
    assert dataset.train_y.loc[0] == 0.01


def test_build_supervised_split_dataset_rejects_invalid_input_types() -> None:
    matrix, standardized = _matrix_and_standardized()

    with pytest.raises(TypeError, match="feature_matrix must be a FeatureMatrix"):
        build_supervised_split_dataset(object(), standardized)  # type: ignore[arg-type]
    with pytest.raises(
        TypeError,
        match="standardized_features must be a StandardizedFeatureMatrix",
    ):
        build_supervised_split_dataset(matrix, object())  # type: ignore[arg-type]


def test_build_supervised_split_dataset_rejects_standardized_split_mismatch() -> None:
    matrix, standardized = _matrix_and_standardized()
    bad_train = standardized.train.copy()
    bad_train.index = pd.Index([9, 10, 11], dtype="int64")
    mismatched = replace(standardized, train=bad_train)

    with pytest.raises(ValueError, match="train_X index must match fitted train_index"):
        build_supervised_split_dataset(matrix, mismatched)


def test_build_supervised_split_dataset_rejects_feature_column_mismatch() -> None:
    matrix, standardized = _matrix_and_standardized()
    bad_validation = standardized.validation.loc[:, ["feature_a", "feature_b"]]
    mismatched = replace(standardized, validation=bad_validation)

    with pytest.raises(
        ValueError,
        match="validation_X columns must match fitted feature_columns",
    ):
        build_supervised_split_dataset(matrix, mismatched)
