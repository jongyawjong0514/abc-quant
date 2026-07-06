from dataclasses import asdict
import json

import pytest

from abc_quant.models import (
    LightGBMDependencyStatus,
    make_default_lightgbm_regressor_params,
)
from abc_quant.pipeline import run_lightgbm_dependency_smoke
import abc_quant.pipeline.lightgbm_diagnostics as lightgbm_diagnostics


def test_lightgbm_dependency_smoke_reports_absent_package_without_importing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"check": 0, "require": 0}

    def fake_check() -> LightGBMDependencyStatus:
        calls["check"] += 1
        return LightGBMDependencyStatus(
            package_name="lightgbm",
            installed=False,
            message="lightgbm missing for test",
        )

    def fake_require() -> object:
        calls["require"] += 1
        raise AssertionError("run_lightgbm_dependency_smoke must not require LightGBM")

    monkeypatch.setattr(lightgbm_diagnostics, "check_lightgbm_dependency", fake_check)
    monkeypatch.setattr(lightgbm_diagnostics, "require_lightgbm", fake_require, raising=False)

    summary = run_lightgbm_dependency_smoke()

    assert calls == {"check": 1, "require": 0}
    assert summary == {
        "package_name": "lightgbm",
        "installed": False,
        "message": "lightgbm missing for test",
        "default_params": asdict(make_default_lightgbm_regressor_params()),
        "default_model_name": "lightgbm_regressor",
        "default_method": "lightgbm_regressor",
        "fitting_enabled": False,
    }
    assert json.loads(json.dumps(summary, sort_keys=True)) == summary


def test_lightgbm_dependency_smoke_reports_available_package_without_importing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"check": 0}

    def fake_check() -> LightGBMDependencyStatus:
        calls["check"] += 1
        return LightGBMDependencyStatus(
            package_name="lightgbm",
            installed=True,
            message="lightgbm available for test",
        )

    monkeypatch.setattr(lightgbm_diagnostics, "check_lightgbm_dependency", fake_check)

    first = run_lightgbm_dependency_smoke()
    second = run_lightgbm_dependency_smoke()

    assert calls == {"check": 2}
    assert first == second
    assert first["package_name"] == "lightgbm"
    assert first["installed"] is True
    assert first["message"] == "lightgbm available for test"
    assert first["fitting_enabled"] is False
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_lightgbm_dependency_smoke_default_params_match_contract() -> None:
    summary = run_lightgbm_dependency_smoke()
    expected_params = asdict(make_default_lightgbm_regressor_params())

    assert summary["default_params"] == expected_params
    assert set(summary["default_params"]) == {
        "objective",
        "n_estimators",
        "learning_rate",
        "num_leaves",
        "min_data_in_leaf",
        "feature_fraction",
        "bagging_fraction",
        "bagging_freq",
        "random_state",
        "verbosity",
    }


def test_lightgbm_dependency_smoke_has_only_expected_top_level_keys() -> None:
    summary = run_lightgbm_dependency_smoke()

    assert set(summary) == {
        "package_name",
        "installed",
        "message",
        "default_params",
        "default_model_name",
        "default_method",
        "fitting_enabled",
    }


def test_lightgbm_dependency_smoke_does_not_expose_decision_or_simulation_keys() -> None:
    summary = run_lightgbm_dependency_smoke()
    forbidden_keys = {
        "winner",
        "rank",
        "ranking",
        "decision",
        "selected_model",
        "selected-model",
        "model_selection",
        "strategy",
        "signal",
        "signals",
        "trading_signals",
        "allocation",
        "allocations",
        "performance_curve",
        "performance-curve",
        "equity_curve",
        "order",
        "orders",
        "position",
        "positions",
        "simulation",
        "simulation_results",
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


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
