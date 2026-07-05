from dataclasses import FrozenInstanceError
from types import ModuleType

import pytest

import abc_quant.models.lightgbm as lightgbm_contract
from abc_quant.models import (
    LightGBMDependencyStatus,
    LightGBMRegressorParams,
    check_lightgbm_dependency,
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
