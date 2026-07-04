"""Train-only ordinary least-squares regression contracts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from abc_quant.models.dataset import SupervisedSplitDataset
from abc_quant.models.predictions import SplitPredictionBundle, build_split_prediction_bundle


@dataclass(frozen=True)
class LinearRegressionResult:
    """Ordinary least-squares fit plus split prediction bundle."""

    model_name: str
    method: str
    feature_columns: tuple[str, ...]
    coefficients: pd.Series
    intercept: float
    training_row_count: int
    prediction_bundle: SplitPredictionBundle


def fit_linear_regression(
    dataset: SupervisedSplitDataset,
    *,
    fit_intercept: bool = True,
    model_name: str = "ordinary_least_squares",
) -> LinearRegressionResult:
    """Fit ordinary least squares from train features and labels only.

    Validation and test features are used only to generate predictions. The
    function does not read validation/test labels, tune parameters, create
    strategy signals, define allocation logic, build performance curves, or run
    simulation engines.
    """
    if not isinstance(dataset, SupervisedSplitDataset):
        raise TypeError("dataset must be a SupervisedSplitDataset")
    if not isinstance(fit_intercept, bool):
        raise TypeError("fit_intercept must be a bool")

    feature_columns = _validate_feature_columns(dataset)
    train_X = _validate_feature_frame(
        dataset.train_X,
        feature_columns,
        "train_X",
        require_non_empty=True,
    )
    train_y = _validate_train_labels(dataset.train_y, train_X.index)

    method = "ols_with_intercept" if fit_intercept else "ols_no_intercept"
    design_matrix = _design_matrix(train_X, fit_intercept=fit_intercept)
    solution, *_ = np.linalg.lstsq(
        design_matrix,
        train_y.to_numpy(dtype="float64"),
        rcond=None,
    )

    if fit_intercept:
        intercept = float(solution[0])
        coefficient_values = solution[1:]
    else:
        intercept = 0.0
        coefficient_values = solution

    coefficients = pd.Series(
        coefficient_values.astype("float64"),
        index=pd.Index(feature_columns),
        name="linear_regression_coefficient",
        dtype="float64",
    )
    prediction_bundle = build_split_prediction_bundle(
        model_name=model_name,
        method=method,
        train_predictions=_predict_split(
            dataset.train_X,
            feature_columns,
            coefficients,
            intercept,
            "train_X",
        ),
        validation_predictions=_predict_split(
            dataset.validation_X,
            feature_columns,
            coefficients,
            intercept,
            "validation_X",
        ),
        test_predictions=_predict_split(
            dataset.test_X,
            feature_columns,
            coefficients,
            intercept,
            "test_X",
        ),
    )

    return LinearRegressionResult(
        model_name=prediction_bundle.model_name,
        method=method,
        feature_columns=feature_columns,
        coefficients=coefficients.copy(deep=True),
        intercept=intercept,
        training_row_count=int(len(train_y)),
        prediction_bundle=prediction_bundle,
    )


def _validate_feature_columns(dataset: SupervisedSplitDataset) -> tuple[str, ...]:
    feature_columns = tuple(str(column) for column in dataset.feature_columns)
    if not feature_columns:
        raise ValueError("linear regression feature_columns must not be empty")
    duplicates = sorted(
        {column for column in feature_columns if feature_columns.count(column) > 1}
    )
    if duplicates:
        raise ValueError(
            "linear regression feature_columns contains duplicates: "
            + ", ".join(duplicates)
        )
    return feature_columns


def _validate_feature_frame(
    features: pd.DataFrame,
    feature_columns: tuple[str, ...],
    name: str,
    *,
    require_non_empty: bool,
) -> pd.DataFrame:
    if not isinstance(features, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")
    if require_non_empty and features.empty:
        raise ValueError("linear regression requires non-empty train data")
    if features.index.has_duplicates:
        raise ValueError(f"{name} index must be unique")
    if tuple(str(column) for column in features.columns) != feature_columns:
        raise ValueError(f"{name} columns must match dataset feature_columns")

    nonnumeric = [
        column for column in feature_columns if not is_numeric_dtype(features[column])
    ]
    if nonnumeric:
        raise ValueError(
            "linear regression feature columns must be numeric: "
            + ", ".join(nonnumeric)
        )
    if features.empty:
        return features.copy(deep=True).astype("float64")
    if features.isna().any().any():
        if name == "train_X":
            raise ValueError("linear regression training features contain missing values")
        raise ValueError(f"{name} features contain missing values")

    numeric_features = features.astype("float64")
    if not np.isfinite(numeric_features.to_numpy(dtype="float64")).all():
        if name == "train_X":
            raise ValueError("linear regression training features must be finite")
        raise ValueError(f"{name} features must be finite")
    return numeric_features.copy(deep=True)


def _validate_train_labels(labels: pd.Series, expected_index: pd.Index) -> pd.Series:
    if not isinstance(labels, pd.Series):
        raise TypeError("train_y must be a pandas Series")
    if labels.empty:
        raise ValueError("linear regression requires non-empty train data")
    if labels.index.has_duplicates:
        raise ValueError("train_y index must be unique")
    if not labels.index.equals(expected_index):
        raise ValueError("train_y index must match train_X index")
    if labels.isna().any():
        raise ValueError("linear regression training labels contain missing values")
    try:
        numeric_labels = pd.to_numeric(labels, errors="raise").astype("float64")
    except (TypeError, ValueError) as exc:
        raise ValueError("linear regression training labels must be numeric") from exc
    if not np.isfinite(numeric_labels.to_numpy(dtype="float64")).all():
        raise ValueError("linear regression training labels must be finite")
    return numeric_labels.copy(deep=True)


def _design_matrix(features: pd.DataFrame, *, fit_intercept: bool) -> np.ndarray:
    feature_values = features.to_numpy(dtype="float64")
    if not fit_intercept:
        return feature_values
    return np.column_stack([np.ones(len(features), dtype="float64"), feature_values])


def _predict_split(
    features: pd.DataFrame,
    feature_columns: tuple[str, ...],
    coefficients: pd.Series,
    intercept: float,
    split_name: str,
) -> pd.Series:
    numeric_features = _validate_feature_frame(
        features,
        feature_columns,
        split_name,
        require_non_empty=False,
    )
    values = (
        numeric_features.to_numpy(dtype="float64")
        @ coefficients.to_numpy(dtype="float64")
        + intercept
    )
    return pd.Series(
        values.astype("float64"),
        index=numeric_features.index.copy(),
        name="linear_regression_prediction",
        dtype="float64",
    )
