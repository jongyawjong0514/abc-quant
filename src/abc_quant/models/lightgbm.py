"""Optional LightGBM dependency guard and parameter contracts."""

from __future__ import annotations

import importlib
import importlib.util
import math
from dataclasses import asdict, dataclass
from types import ModuleType
from typing import Any, Final

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from abc_quant.models.dataset import SupervisedSplitDataset
from abc_quant.models.predictions import SplitPredictionBundle, build_split_prediction_bundle


LIGHTGBM_PACKAGE_NAME: Final[str] = "lightgbm"


@dataclass(frozen=True)
class LightGBMDependencyStatus:
    """Availability status for the optional LightGBM package."""

    package_name: str
    installed: bool
    message: str


@dataclass(frozen=True)
class LightGBMRegressorParams:
    """Validated deterministic LightGBM regressor parameter contract.

    This dataclass only validates parameters for a future optional estimator. It
    does not import LightGBM, fit models, search parameters, select models,
    generate strategy signals, or run simulations.
    """

    objective: str = "regression"
    n_estimators: int = 100
    learning_rate: float = 0.05
    num_leaves: int = 31
    min_data_in_leaf: int = 20
    feature_fraction: float = 1.0
    bagging_fraction: float = 1.0
    bagging_freq: int = 0
    random_state: int = 42
    verbosity: int = -1

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.objective, "objective")
        _validate_positive_integer(self.n_estimators, "n_estimators")
        _validate_positive_number(self.learning_rate, "learning_rate")
        _validate_integer_at_least(self.num_leaves, "num_leaves", minimum=2)
        _validate_positive_integer(self.min_data_in_leaf, "min_data_in_leaf")
        _validate_fraction(self.feature_fraction, "feature_fraction")
        _validate_fraction(self.bagging_fraction, "bagging_fraction")
        _validate_nonnegative_integer(self.bagging_freq, "bagging_freq")
        _validate_integer(self.random_state, "random_state")
        _validate_integer(self.verbosity, "verbosity")


@dataclass(frozen=True)
class LightGBMRegressorResult:
    """LightGBM fit metadata plus split prediction bundle."""

    model_name: str
    method: str
    feature_columns: tuple[str, ...]
    params: LightGBMRegressorParams
    training_row_count: int
    prediction_bundle: SplitPredictionBundle


def check_lightgbm_dependency() -> LightGBMDependencyStatus:
    """Return optional LightGBM availability without importing the package."""
    package_name = LIGHTGBM_PACKAGE_NAME
    package_spec = importlib.util.find_spec(package_name)
    if package_spec is None:
        return LightGBMDependencyStatus(
            package_name=package_name,
            installed=False,
            message=(
                "Optional dependency 'lightgbm' is not installed; install it "
                "before using LightGBM model contracts that require the package."
            ),
        )
    return LightGBMDependencyStatus(
        package_name=package_name,
        installed=True,
        message="Optional dependency 'lightgbm' is available.",
    )


def require_lightgbm() -> ModuleType:
    """Return the imported LightGBM module or raise a clear ImportError."""
    status = check_lightgbm_dependency()
    if not status.installed:
        raise ImportError(status.message)
    try:
        return importlib.import_module(status.package_name)
    except ImportError as exc:
        raise ImportError(
            "Optional dependency 'lightgbm' was detected but could not be imported."
        ) from exc


def make_default_lightgbm_regressor_params() -> LightGBMRegressorParams:
    """Return deterministic conservative default LightGBM regressor parameters."""
    return LightGBMRegressorParams()


def fit_lightgbm_regressor(
    dataset: SupervisedSplitDataset,
    *,
    params: LightGBMRegressorParams | None = None,
    model_name: str = "lightgbm_regressor",
) -> LightGBMRegressorResult:
    """Fit a LightGBM regressor from train features and labels only.

    LightGBM is an optional dependency. This function imports it only through
    `require_lightgbm()`. Validation and test features are used only to
    generate predictions. Validation and test labels are not read by this
    fitting path.
    """
    if not isinstance(dataset, SupervisedSplitDataset):
        raise TypeError("dataset must be a SupervisedSplitDataset")
    fitted_params = make_default_lightgbm_regressor_params() if params is None else params
    if not isinstance(fitted_params, LightGBMRegressorParams):
        raise TypeError("params must be a LightGBMRegressorParams")

    feature_columns = _validate_feature_columns(dataset)
    train_X = _validate_feature_frame(
        dataset.train_X,
        feature_columns,
        "train_X",
        require_non_empty=True,
    )
    train_y = _validate_train_labels(dataset.train_y, train_X.index)

    lightgbm_module = require_lightgbm()
    estimator_type = getattr(lightgbm_module, "LGBMRegressor", None)
    if estimator_type is None:
        raise ImportError("Optional dependency 'lightgbm' does not expose LGBMRegressor.")

    estimator = estimator_type(**asdict(fitted_params))
    estimator.fit(train_X, train_y)

    method = "lightgbm_regressor"
    prediction_bundle = build_split_prediction_bundle(
        model_name=model_name,
        method=method,
        train_predictions=_predict_split(
            estimator,
            dataset.train_X,
            feature_columns,
            "train_X",
        ),
        validation_predictions=_predict_split(
            estimator,
            dataset.validation_X,
            feature_columns,
            "validation_X",
        ),
        test_predictions=_predict_split(
            estimator,
            dataset.test_X,
            feature_columns,
            "test_X",
        ),
    )

    return LightGBMRegressorResult(
        model_name=prediction_bundle.model_name,
        method=method,
        feature_columns=feature_columns,
        params=fitted_params,
        training_row_count=int(len(train_y)),
        prediction_bundle=prediction_bundle,
    )


def _validate_feature_columns(dataset: SupervisedSplitDataset) -> tuple[str, ...]:
    feature_columns = tuple(str(column) for column in dataset.feature_columns)
    if not feature_columns:
        raise ValueError("LightGBM regressor feature_columns must not be empty")
    duplicates = sorted(
        {column for column in feature_columns if feature_columns.count(column) > 1}
    )
    if duplicates:
        raise ValueError(
            "LightGBM regressor feature_columns contains duplicates: "
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
        raise ValueError("LightGBM regressor requires non-empty train data")
    if features.index.has_duplicates:
        raise ValueError(f"{name} index must be unique")
    if tuple(str(column) for column in features.columns) != feature_columns:
        raise ValueError(f"{name} columns must match dataset feature_columns")

    nonnumeric = [
        column for column in feature_columns if not is_numeric_dtype(features[column])
    ]
    if nonnumeric:
        raise ValueError(
            "LightGBM regressor feature columns must be numeric: "
            + ", ".join(nonnumeric)
        )
    if features.empty:
        return features.copy(deep=True).astype("float64")
    if features.isna().any().any():
        if name == "train_X":
            raise ValueError("LightGBM regressor training features contain missing values")
        raise ValueError(f"{name} features contain missing values")

    numeric_features = features.astype("float64")
    if not np.isfinite(numeric_features.to_numpy(dtype="float64")).all():
        if name == "train_X":
            raise ValueError("LightGBM regressor training features must be finite")
        raise ValueError(f"{name} features must be finite")
    return numeric_features.copy(deep=True)


def _validate_train_labels(labels: pd.Series, expected_index: pd.Index) -> pd.Series:
    if not isinstance(labels, pd.Series):
        raise TypeError("train_y must be a pandas Series")
    if labels.empty:
        raise ValueError("LightGBM regressor requires non-empty train data")
    if labels.index.has_duplicates:
        raise ValueError("train_y index must be unique")
    if not labels.index.equals(expected_index):
        raise ValueError("train_y index must match train_X index")
    if labels.isna().any():
        raise ValueError("LightGBM regressor training labels contain missing values")
    try:
        numeric_labels = pd.to_numeric(labels, errors="raise").astype("float64")
    except (TypeError, ValueError) as exc:
        raise ValueError("LightGBM regressor training labels must be numeric") from exc
    if not np.isfinite(numeric_labels.to_numpy(dtype="float64")).all():
        raise ValueError("LightGBM regressor training labels must be finite")
    return numeric_labels.copy(deep=True)


def _predict_split(
    estimator: Any,
    features: pd.DataFrame,
    feature_columns: tuple[str, ...],
    split_name: str,
) -> pd.Series:
    numeric_features = _validate_feature_frame(
        features,
        feature_columns,
        split_name,
        require_non_empty=False,
    )
    if numeric_features.empty:
        return pd.Series(
            [],
            index=numeric_features.index.copy(),
            name="lightgbm_regressor_prediction",
            dtype="float64",
        )

    predictions = estimator.predict(numeric_features)
    if len(predictions) != len(numeric_features):
        raise ValueError(f"{split_name} prediction count must match feature row count")
    return pd.Series(
        np.asarray(predictions, dtype="float64"),
        index=numeric_features.index.copy(),
        name="lightgbm_regressor_prediction",
        dtype="float64",
    )


def _validate_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")


def _validate_positive_integer(value: int, field_name: str) -> None:
    _validate_integer(value, field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _validate_integer_at_least(value: int, field_name: str, *, minimum: int) -> None:
    _validate_integer(value, field_name)
    if value < minimum:
        raise ValueError(f"{field_name} must be at least {minimum}")


def _validate_nonnegative_integer(value: int, field_name: str) -> None:
    _validate_integer(value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")


def _validate_positive_number(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be positive")
    if not math.isfinite(float(value)) or float(value) <= 0.0:
        raise ValueError(f"{field_name} must be positive")


def _validate_fraction(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be in (0, 1]")
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value <= 0.0 or numeric_value > 1.0:
        raise ValueError(f"{field_name} must be in (0, 1]")
