from dataclasses import asdict, replace
import json
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

import abc_quant.models.lightgbm as lightgbm_contract
from abc_quant.models.lightgbm import make_default_lightgbm_regressor_params
from abc_quant.pipeline import (
    LIGHTGBM_EVALUATION_SMOKE_DEFAULT_PARAM_KEYS,
    LIGHTGBM_EVALUATION_SMOKE_EVALUATION_KEYS,
    LIGHTGBM_EVALUATION_SMOKE_FORBIDDEN_KEYS,
    LIGHTGBM_EVALUATION_SMOKE_SPLITS,
    LIGHTGBM_EVALUATION_SMOKE_SUMMARY_KEYS,
    run_lightgbm_evaluation_smoke,
    validate_lightgbm_evaluation_smoke_summary,
)
import abc_quant.pipeline.lightgbm_evaluation as lightgbm_evaluation


def test_lightgbm_evaluation_smoke_default_is_dependency_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"fit": 0, "import": 0}

    def fake_fit(*args: object, **kwargs: object) -> object:
        calls["fit"] += 1
        raise AssertionError("default LightGBM evaluation smoke must not fit")

    def fake_import_module(name: str) -> ModuleType:
        calls["import"] += 1
        raise AssertionError("default LightGBM evaluation smoke must not import")

    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(lightgbm_contract.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(lightgbm_evaluation, "fit_lightgbm_regressor", fake_fit)

    summary = run_lightgbm_evaluation_smoke()

    assert calls == {"fit": 0, "import": 0}
    assert tuple(summary) == LIGHTGBM_EVALUATION_SMOKE_SUMMARY_KEYS
    assert summary["package_name"] == "lightgbm"
    assert summary["installed"] is False
    assert summary["fitting_enabled"] is False
    assert summary["fitted"] is False
    assert summary["unavailable_reason"] is None
    assert summary["model_name"] is None
    assert summary["method"] is None
    assert summary["feature_columns"] == []
    assert summary["training_row_count"] == 0
    assert summary["evaluation"] is None
    assert summary["default_params"] == asdict(make_default_lightgbm_regressor_params())
    assert tuple(summary["default_params"]) == LIGHTGBM_EVALUATION_SMOKE_DEFAULT_PARAM_KEYS
    assert validate_lightgbm_evaluation_smoke_summary(summary) is summary
    assert json.loads(json.dumps(summary, sort_keys=True)) == summary


def test_lightgbm_evaluation_smoke_explicit_fit_unavailable_does_not_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"fit": 0, "import": 0}

    def fake_fit(*args: object, **kwargs: object) -> object:
        calls["fit"] += 1
        raise AssertionError("unavailable LightGBM evaluation smoke must not fit")

    def fake_import_module(name: str) -> ModuleType:
        calls["import"] += 1
        raise AssertionError("unavailable LightGBM evaluation smoke must not import")

    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(lightgbm_contract.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(lightgbm_evaluation, "fit_lightgbm_regressor", fake_fit)

    summary = run_lightgbm_evaluation_smoke(fitting_enabled=True)

    assert calls == {"fit": 0, "import": 0}
    assert summary["fitting_enabled"] is True
    assert summary["fitted"] is False
    assert summary["installed"] is False
    assert "not installed" in str(summary["unavailable_reason"])
    assert summary["evaluation"] is None
    assert validate_lightgbm_evaluation_smoke_summary(summary) is summary


def test_lightgbm_evaluation_smoke_fake_fit_returns_deterministic_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, fake_estimator = _install_fake_lightgbm(monkeypatch)

    first = run_lightgbm_evaluation_smoke(fitting_enabled=True)
    second = run_lightgbm_evaluation_smoke(fitting_enabled=True)

    assert first == second
    assert len(fake_estimator.instances) == 2
    assert first["fitting_enabled"] is True
    assert first["fitted"] is True
    assert first["installed"] is True
    assert first["unavailable_reason"] is None
    assert first["model_name"] == "lightgbm_regressor"
    assert first["method"] == "lightgbm_regressor"
    assert first["feature_columns"] == [
        "price_momentum_1d",
        "price_momentum_3d",
        "price_volatility_3d",
        "volume_average_3d",
    ]
    assert first["training_row_count"] == 2
    assert set(first["evaluation"]) == LIGHTGBM_EVALUATION_SMOKE_SPLITS
    for split_name in sorted(LIGHTGBM_EVALUATION_SMOKE_SPLITS):
        metrics = first["evaluation"][split_name]
        assert set(metrics) == LIGHTGBM_EVALUATION_SMOKE_EVALUATION_KEYS
        assert metrics["split_name"] == split_name
        assert metrics["row_count"] > 0
    assert validate_lightgbm_evaluation_smoke_summary(first) is first
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_lightgbm_evaluation_smoke_does_not_use_holdout_labels_for_fit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, fake_estimator = _install_fake_lightgbm(monkeypatch)
    baseline = run_lightgbm_evaluation_smoke(fitting_enabled=True)
    original_builder = lightgbm_evaluation.build_supervised_split_dataset

    def changed_holdout_label_builder(*args: object, **kwargs: object):
        dataset = original_builder(*args, **kwargs)
        return replace(
            dataset,
            validation_y=pd.Series(
                [-999.0] * len(dataset.validation_y),
                index=dataset.validation_y.index,
            ),
            test_y=pd.Series(
                [999.0] * len(dataset.test_y),
                index=dataset.test_y.index,
            ),
        )

    monkeypatch.setattr(
        lightgbm_evaluation,
        "build_supervised_split_dataset",
        changed_holdout_label_builder,
    )
    changed = run_lightgbm_evaluation_smoke(fitting_enabled=True)

    assert baseline == changed
    assert len(fake_estimator.instances) == 2
    pd.testing.assert_frame_equal(
        fake_estimator.instances[0].fit_X,
        fake_estimator.instances[1].fit_X,
    )
    pd.testing.assert_series_equal(
        fake_estimator.instances[0].fit_y,
        fake_estimator.instances[1].fit_y,
    )


def test_lightgbm_evaluation_smoke_summary_validator_rejects_invalid_shapes() -> None:
    summary = _valid_default_summary()
    summary.pop("message")
    with pytest.raises(ValueError, match="missing=\\['message'\\]"):
        validate_lightgbm_evaluation_smoke_summary(summary)

    summary = _valid_default_summary()
    summary["unexpected"] = "value"
    with pytest.raises(ValueError, match="unknown=\\['unexpected'\\]"):
        validate_lightgbm_evaluation_smoke_summary(summary)

    summary = _valid_default_summary()
    summary["default_params"] = ["objective"]
    with pytest.raises(ValueError, match="default_params must be a dict"):
        validate_lightgbm_evaluation_smoke_summary(summary)

    summary = _valid_default_summary()
    summary["default_params"].pop("objective")
    with pytest.raises(ValueError, match="missing=\\['objective'\\]"):
        validate_lightgbm_evaluation_smoke_summary(summary)

    summary = _valid_fitted_summary()
    summary["evaluation"]["train"].pop("mae")
    with pytest.raises(ValueError, match="missing=\\['mae'\\]"):
        validate_lightgbm_evaluation_smoke_summary(summary)

    summary = _valid_default_summary()
    summary["default_params"]["learning_rate"] = float("nan")
    with pytest.raises(ValueError, match="must be JSON-friendly"):
        validate_lightgbm_evaluation_smoke_summary(summary)

    summary = _valid_default_summary()
    summary["evaluation"] = {"train": {"strategy": "not allowed"}}
    with pytest.raises(ValueError, match="forbidden keys: strategy"):
        validate_lightgbm_evaluation_smoke_summary(summary)


def test_lightgbm_evaluation_smoke_summary_validator_rejects_non_dict() -> None:
    with pytest.raises(TypeError, match="must be a dict"):
        validate_lightgbm_evaluation_smoke_summary(["not", "a", "dict"])


def test_lightgbm_evaluation_smoke_does_not_expose_forbidden_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_lightgbm(monkeypatch)

    summaries = [
        run_lightgbm_evaluation_smoke(),
        run_lightgbm_evaluation_smoke(fitting_enabled=True),
    ]

    for summary in summaries:
        assert set(LIGHTGBM_EVALUATION_SMOKE_FORBIDDEN_KEYS).isdisjoint(
            _all_dict_keys(summary)
        )


def _install_fake_lightgbm(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, type]:
    fake_module, fake_estimator = _fake_lightgbm_module()
    monkeypatch.setattr(lightgbm_contract.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(
        lightgbm_contract.importlib,
        "import_module",
        lambda name: fake_module,
    )
    return fake_module, fake_estimator


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


def _valid_default_summary() -> dict[str, object]:
    return {
        "package_name": "lightgbm",
        "installed": False,
        "message": "fake dependency status",
        "default_params": asdict(make_default_lightgbm_regressor_params()),
        "fitting_enabled": False,
        "fitted": False,
        "unavailable_reason": None,
        "model_name": None,
        "method": None,
        "feature_columns": [],
        "training_row_count": 0,
        "evaluation": None,
    }


def _valid_fitted_summary() -> dict[str, object]:
    metrics = {
        "split_name": "train",
        "row_count": 1,
        "non_missing_count": 1,
        "missing_actual_count": 0,
        "mae": 0.0,
        "rmse": 0.0,
        "mean_error": 0.0,
        "prediction_mean": 1.0,
    }
    summary = _valid_default_summary()
    summary.update(
        {
            "installed": True,
            "message": "fake dependency available",
            "fitting_enabled": True,
            "fitted": True,
            "model_name": "lightgbm_regressor",
            "method": "lightgbm_regressor",
            "feature_columns": ["feature_a"],
            "training_row_count": 1,
            "evaluation": {
                "train": dict(metrics),
                "validation": {**metrics, "split_name": "validation"},
                "test": {**metrics, "split_name": "test"},
            },
        }
    )
    return summary


def _all_dict_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_all_dict_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_dict_keys(item))
        return keys
    return set()
