from dataclasses import replace

import pandas as pd
import pytest

from abc_quant.features.matrix import FeatureMatrix, build_feature_matrix
from abc_quant.preprocessing.scaling import (
    StandardScalerFit,
    StandardizedFeatureMatrix,
    fit_standard_scaler,
    transform_with_standard_scaler,
)
from abc_quant.validation.temporal import TemporalSplit, build_temporal_split


LABEL_COLUMN = "label_forward_return"


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=6, freq="D"),
            "ticker": ["2330"] * 6,
            "open": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            "high": [11.0, 12.0, 13.0, 14.0, 15.0, 16.0],
            "low": [9.0, 10.0, 11.0, 12.0, 13.0, 14.0],
            "close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500],
            "feature_a": [1.0, 3.0, 5.0, 999.0, -999.0, 1500.0],
            "feature_b": [10.0, 14.0, 18.0, -500.0, 700.0, -900.0],
            LABEL_COLUMN: [0.01, 0.02, 0.03, 0.04, pd.NA, 0.06],
        }
    )


def _matrix_and_split() -> tuple[FeatureMatrix, TemporalSplit]:
    matrix = build_feature_matrix(_frame(), LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-03",
        validation_end="2026-01-04",
    )
    return matrix, split


def test_fit_standard_scaler_uses_training_rows_only() -> None:
    matrix, split = _matrix_and_split()

    fitted = fit_standard_scaler(matrix, split)

    assert isinstance(fitted, StandardScalerFit)
    assert fitted.feature_columns == ("feature_a", "feature_b")
    pd.testing.assert_series_equal(
        fitted.means,
        pd.Series({"feature_a": 3.0, "feature_b": 14.0}),
        check_names=False,
    )
    pd.testing.assert_series_equal(
        fitted.stds,
        pd.Series({"feature_a": 1.632993161855452, "feature_b": 3.265986323710904}),
        check_names=False,
    )
    assert fitted.train_index == split.train_index
    assert fitted.validation_index == split.validation_index
    assert fitted.test_index == split.test_index


def test_transform_with_standard_scaler_preserves_split_indices_counts_and_columns() -> None:
    matrix, split = _matrix_and_split()
    fitted = fit_standard_scaler(matrix, split, feature_columns=["feature_b", "feature_a"])

    standardized = transform_with_standard_scaler(matrix, fitted, split)

    assert isinstance(standardized, StandardizedFeatureMatrix)
    assert standardized.fitted is fitted
    assert list(standardized.train.columns) == ["feature_b", "feature_a"]
    assert list(standardized.validation.columns) == ["feature_b", "feature_a"]
    assert list(standardized.test.columns) == ["feature_b", "feature_a"]
    assert tuple(standardized.train.index) == split.train_index
    assert tuple(standardized.validation.index) == split.validation_index
    assert tuple(standardized.test.index) == split.test_index
    assert len(standardized.train) == len(split.train_index)
    assert len(standardized.validation) == len(split.validation_index)
    assert len(standardized.test) == len(split.test_index)
    pd.testing.assert_series_equal(
        standardized.train.mean(axis=0),
        pd.Series({"feature_b": 0.0, "feature_a": 0.0}),
        check_names=False,
        atol=1e-12,
    )
    pd.testing.assert_series_equal(
        standardized.train.std(axis=0, ddof=0),
        pd.Series({"feature_b": 1.0, "feature_a": 1.0}),
        check_names=False,
    )


def test_validation_and_test_extremes_do_not_change_fit() -> None:
    base_frame = _frame()
    extreme_frame = base_frame.copy()
    extreme_frame.loc[3:, "feature_a"] = [1_000_000.0, -1_000_000.0, 500_000.0]
    extreme_frame.loc[3:, "feature_b"] = [-2_000_000.0, 2_000_000.0, -750_000.0]
    base_matrix = build_feature_matrix(base_frame, LABEL_COLUMN)
    extreme_matrix = build_feature_matrix(extreme_frame, LABEL_COLUMN)
    split = build_temporal_split(
        base_matrix.metadata,
        train_end="2026-01-03",
        validation_end="2026-01-04",
    )

    base_fit = fit_standard_scaler(base_matrix, split)
    extreme_fit = fit_standard_scaler(extreme_matrix, split)

    pd.testing.assert_series_equal(base_fit.means, extreme_fit.means)
    pd.testing.assert_series_equal(base_fit.stds, extreme_fit.stds)


def test_fit_standard_scaler_rejects_invalid_feature_columns() -> None:
    matrix, split = _matrix_and_split()

    with pytest.raises(ValueError, match="unknown"):
        fit_standard_scaler(matrix, split, feature_columns=["missing_feature"])
    with pytest.raises(ValueError, match="duplicates"):
        fit_standard_scaler(matrix, split, feature_columns=["feature_a", "feature_a"])


def test_fit_standard_scaler_rejects_nonnumeric_columns() -> None:
    frame = _frame()
    frame["feature_text"] = ["a", "b", "c", "d", "e", "f"]
    matrix = build_feature_matrix(frame, LABEL_COLUMN, feature_columns=["feature_text"])
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-03",
        validation_end="2026-01-04",
    )

    with pytest.raises(ValueError, match="must be numeric"):
        fit_standard_scaler(matrix, split)


def test_fit_standard_scaler_rejects_missing_training_values() -> None:
    frame = _frame()
    frame.loc[1, "feature_a"] = pd.NA
    matrix = build_feature_matrix(frame, LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-03",
        validation_end="2026-01-04",
    )

    with pytest.raises(ValueError, match="missing values"):
        fit_standard_scaler(matrix, split)


def test_fit_standard_scaler_rejects_zero_variance_training_features() -> None:
    frame = _frame()
    frame.loc[:2, "feature_a"] = 7.0
    matrix = build_feature_matrix(frame, LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-03",
        validation_end="2026-01-04",
    )

    with pytest.raises(ValueError, match="zero variance"):
        fit_standard_scaler(matrix, split, feature_columns=["feature_a"])


def test_fit_standard_scaler_rejects_empty_train_split() -> None:
    matrix, split = _matrix_and_split()
    empty_train_split = replace(split, train_index=())

    with pytest.raises(ValueError, match="non-empty train"):
        fit_standard_scaler(matrix, empty_train_split)


def test_transform_with_standard_scaler_rejects_split_mismatch() -> None:
    matrix, split = _matrix_and_split()
    fitted = fit_standard_scaler(matrix, split)
    mismatched_split = replace(split, validation_index=())

    with pytest.raises(ValueError, match="validation_index"):
        transform_with_standard_scaler(matrix, fitted, mismatched_split)
