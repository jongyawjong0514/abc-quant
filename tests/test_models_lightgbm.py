from dataclasses import FrozenInstanceError, replace
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

import abc_quant.models.lightgbm as lightgbm_contract
from abc_quant.models import (
    LightGBMDependencyStatus,
    LightGBMRegressorParams,
    LightGBMRegressorResult,
    SplitPredictionBundle,
    SupervisedSplitDataset,
    check_lightgbm_dependency,
    fit_lightgbm_regressor,
    make_default_lightgbm_regressor_params,
    require_lightgbm,
)


def test_lightgbm_module_imports_without_optional_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: None)

    status = lightgbm_contract.check_lightgbm_dependency()

    assert status == LightGBMDependencyStatus(
        package_name="lightgbm",
        installed=False,
        message=(
            "Optional dependency 'lightgbm' is not installed; install it before using "
            "LightGBM model contracts that require the package."
        ),
    )
    with pytest.raises(ImportError, match="Optional dependency 'lightgbm' is not installed"):
        lightgbm_contract.require_lightgbm()


def test_check_lightgbm_dependency_does_not_import_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported_names: list[str] = []

    def fake_import_module(name: str) -> ModuleType:
        imported_names.append(name)
        return ModuleType(name)

    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(lightgbm_contract.importlib, "import_module", fake_import_module)

    status = check_lightgbm_dependency()

    assert status.package_name == "lightgbm"
    assert status.installed is True
    assert status.message == "Optional dependency 'lightgbm' is available."
    assert imported_names == []


def test_require_lightgbm_imports_optional_package_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_lightgbm = ModuleType("lightgbm")
    imported_names: list[str] = []

    def fake_import_module(name: str) -> ModuleType:
        imported_names.append(name)
        return fake_lightgbm

    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(lightgbm_contract.importlib, "import_module", fake_import_module)

    imported_module = require_lightgbm()

    assert imported_module is fake_lightgbm
    assert imported_names == ["lightgbm"]


def test_require_lightgbm_wraps_import_error_after_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_module(name: str) -> ModuleType:
        raise ImportError("broken optional install")

    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(lightgbm_contract.importlib, "import_module", fake_import_module)

    with pytest.raises(ImportError, match="detected but could not be imported"):
        require_lightgbm()


def test_default_lightgbm_regressor_params_are_deterministic_and_valid() -> None:
    first = make_default_lightgbm_regressor_params()
    second = make_default_lightgbm_regressor_params()

    assert first == second
    assert first == LightGBMRegressorParams(
        objective="regression",
        n_estimators=100,
        learning_rate=0.05,
        num_leaves=31,
        min_data_in_leaf=20,
        feature_fraction=1.0,
        bagging_fraction=1.0,
        bagging_freq=0,
        random_state=42,
        verbosity=-1,
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"objective": ""}, "objective must be a non-empty string"),
        ({"objective": "   "}, "objective must be a non-empty string"),
        ({"objective": 123}, "objective must be a non-empty string"),
        ({"n_estimators": 0}, "n_estimators must be positive"),
        ({"n_estimators": True}, "n_estimators must be an integer"),
        ({"learning_rate": 0.0}, "learning_rate must be positive"),
        ({"learning_rate": float("inf")}, "learning_rate must be positive"),
        ({"num_leaves": 1}, "num_leaves must be at least 2"),
        ({"min_data_in_leaf": 0}, "min_data_in_leaf must be positive"),
        ({"feature_fraction": 0.0}, "feature_fraction must be in \\(0, 1\\]"),
        ({"feature_fraction": 1.01}, "feature_fraction must be in \\(0, 1\\]"),
        ({"bagging_fraction": 0.0}, "bagging_fraction must be in \\(0, 1\\]"),
        ({"bagging_fraction": float("nan")}, "bagging_fraction must be in \\(0, 1\\]"),
        ({"bagging_freq": -1}, "bagging_freq must be nonnegative"),
        ({"random_state": 42.5}, "random_state must be an integer"),
        ({"random_state": False}, "random_state must be an integer"),
        ({"verbosity": "silent"}, "verbosity must be an integer"),
    ],
)
def test_lightgbm_regressor_params_reject_invalid_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        LightGBMRegressorParams(**kwargs)  # type: ignore[arg-type]


def test_lightgbm_regressor_params_are_frozen() -> None:
    params = make_default_lightgbm_regressor_params()

    with pytest.raises(FrozenInstanceError):
        params.n_estimators = 200  # type: ignore[misc]


def test_fit_lightgbm_regressor_raises_clear_import_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: None)

    with pytest.raises(ImportError, match="Optional dependency 'lightgbm' is not installed"):
        fit_lightgbm_regressor(_dataset())


def test_fit_lightgbm_regressor_uses_train_data_and_passes_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module, fake_estimator = _fake_lightgbm_module()
    _install_fake_lightgbm(monkeypatch, fake_module)
    dataset = _dataset()
    params = LightGBMRegressorParams(n_estimators=7, learning_rate=0.2, num_leaves=5)

    result = fit_lightgbm_regressor(
        dataset,
        params=params,
        model_name="  lightgbm_candidate  ",
    )

    assert isinstance(result, LightGBMRegressorResult)
    assert isinstance(result.prediction_bundle, SplitPredictionBundle)
    assert result.model_name == "lightgbm_candidate"
    assert result.method == "lightgbm_regressor"
    assert result.feature_columns == ("feature_a", "feature_b")
    assert result.params == params
    assert result.training_row_count == len(dataset.train_y)
    assert len(fake_estimator.instances) == 1
    fitted_estimator = fake_estimator.instances[0]
    assert fitted_estimator.params["n_estimators"] == 7
    assert fitted_estimator.params["learning_rate"] == 0.2
    assert fitted_estimator.params["num_leaves"] == 5
    pd.testing.assert_frame_equal(fitted_estimator.fit_X, dataset.train_X)
    pd.testing.assert_series_equal(fitted_estimator.fit_y, dataset.train_y)
    _assert_prediction_index(result.prediction_bundle.train_predictions, dataset.train_X)
    _assert_prediction_index(
        result.prediction_bundle.validation_predictions,
        dataset.validation_X,
    )
    _assert_prediction_index(result.prediction_bundle.test_predictions, dataset.test_X)


def test_fit_lightgbm_regressor_ignores_validation_and_test_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module, fake_estimator = _fake_lightgbm_module()
    _install_fake_lightgbm(monkeypatch, fake_module)
    dataset = _dataset()
    changed_holdout_labels = replace(
        dataset,
        validation_y=pd.Series([-999.0, -888.0], index=dataset.validation_y.index),
        test_y=pd.Series([777.0, 888.0], index=dataset.test_y.index),
    )

    baseline = fit_lightgbm_regressor(dataset)
    changed = fit_lightgbm_regressor(changed_holdout_labels)

    assert len(fake_estimator.instances) == 2
    pd.testing.assert_series_equal(
        fake_estimator.instances[0].fit_y,
        fake_estimator.instances[1].fit_y,
    )
    pd.testing.assert_series_equal(
        changed.prediction_bundle.train_predictions,
        baseline.prediction_bundle.train_predictions,
    )
    pd.testing.assert_series_equal(
        changed.prediction_bundle.validation_predictions,
        baseline.prediction_bundle.validation_predictions,
    )
    pd.testing.assert_series_equal(
        changed.prediction_bundle.test_predictions,
        baseline.prediction_bundle.test_predictions,
    )


def test_fit_lightgbm_regressor_rejects_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module, _ = _fake_lightgbm_module()
    _install_fake_lightgbm(monkeypatch, fake_module)
    dataset = _dataset()

    with pytest.raises(TypeError, match="dataset must be a SupervisedSplitDataset"):
        fit_lightgbm_regressor(object())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="params must be a LightGBMRegressorParams"):
        fit_lightgbm_regressor(dataset, params=object())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="non-empty train data"):
        fit_lightgbm_regressor(
            replace(
                dataset,
                train_X=dataset.train_X.iloc[0:0],
                train_y=dataset.train_y.iloc[0:0],
            )
        )

    with pytest.raises(ValueError, match="training features contain missing values"):
        fit_lightgbm_regressor(
            replace(
                dataset,
                train_X=dataset.train_X.assign(feature_a=[0.0, np.nan, 2.0, 3.0]),
            )
        )

    with pytest.raises(ValueError, match="training labels contain missing values"):
        fit_lightgbm_regressor(
            replace(
                dataset,
                train_y=pd.Series([1.0, np.nan, 2.0, 3.0], index=dataset.train_X.index),
            )
        )

    with pytest.raises(ValueError, match="feature columns must be numeric"):
        fit_lightgbm_regressor(
            replace(
                dataset,
                train_X=dataset.train_X.assign(feature_a=["x", "y", "z", "w"]),
            )
        )


def _dataset() -> SupervisedSplitDataset:
    feature_columns = ("feature_a", "feature_b")
    train_X = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 2.0, 3.0],
            "feature_b": [1.0, 0.0, 2.0, 1.0],
        },
        index=pd.Index([0, 1, 2, 3], dtype="int64"),
    )
    validation_X = pd.DataFrame(
        {
            "feature_a": [4.0, 5.0],
            "feature_b": [0.0, 2.0],
        },
        index=pd.Index([10, 11], dtype="int64"),
    )
    test_X = pd.DataFrame(
        {
            "feature_a": [6.0, 7.0],
            "feature_b": [1.0, 3.0],
        },
        index=pd.Index([20, 21], dtype="int64"),
    )
    return SupervisedSplitDataset(
        feature_columns=feature_columns,
        label_column="label_forward_return",
        train_X=train_X,
        train_y=pd.Series([1.0, 2.0, 3.0, 4.0], index=train_X.index),
        validation_X=validation_X,
        validation_y=pd.Series([100.0, 200.0], index=validation_X.index),
        test_X=test_X,
        test_y=pd.Series([300.0, 400.0], index=test_X.index),
        dropped_label_counts={"train": 0, "validation": 0, "test": 0},
    )


def _fake_lightgbm_module() -> tuple[ModuleType, type]:
    class FakeLGBMRegressor:
        instances: list["FakeLGBMRegressor"] = []

        def __init__(self, **params: object) -> None:
            self.params = params
            self.fit_X: pd.DataFrame | None = None
            self.fit_y: pd.Series | None = None
            self.bias = 0.0
            self.instances.append(self)

        def fit(self, X: pd.DataFrame, y: pd.Series) -> "FakeLGBMRegressor":
            self.fit_X = X.copy(deep=True)
            self.fit_y = y.copy(deep=True)
            self.bias = float(y.mean())
            return self

        def predict(self, X: pd.DataFrame) -> np.ndarray:
            return X.sum(axis=1).to_numpy(dtype="float64") + self.bias

    fake_module = ModuleType("lightgbm")
    setattr(fake_module, "LGBMRegressor", FakeLGBMRegressor)
    return fake_module, FakeLGBMRegressor


def _install_fake_lightgbm(
    monkeypatch: pytest.MonkeyPatch,
    fake_module: ModuleType,
) -> None:
    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(
        lightgbm_contract.importlib,
        "import_module",
        lambda name: fake_module,
    )


def _assert_prediction_index(predictions: pd.Series, features: pd.DataFrame) -> None:
    assert tuple(predictions.index) == tuple(features.index)
