from dataclasses import asdict
import json

import pytest

from abc_quant.models import (
    LightGBMDependencyStatus,
    make_default_lightgbm_regressor_params,
)
from abc_quant.pipeline import run_lightgbm_dependency_smoke
from abc_quant.pipeline.lightgbm_diagnostics import (
    LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS,
    LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS,
    LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS,
    validate_lightgbm_dependency_smoke_summary,
)
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


def test_lightgbm_dependency_smoke_calls_summary_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"validate": 0}

    def fake_check() -> LightGBMDependencyStatus:
        return LightGBMDependencyStatus(
            package_name="lightgbm",
            installed=False,
            message="lightgbm missing for validator call test",
        )

    def fake_validate(summary: object) -> dict[str, object]:
        calls["validate"] += 1
        assert isinstance(summary, dict)
        return summary

    monkeypatch.setattr(lightgbm_diagnostics, "check_lightgbm_dependency", fake_check)
    monkeypatch.setattr(
        lightgbm_diagnostics,
        "validate_lightgbm_dependency_smoke_summary",
        fake_validate,
    )

    summary = run_lightgbm_dependency_smoke()

    assert calls == {"validate": 1}
    assert summary["package_name"] == "lightgbm"
    assert summary["fitting_enabled"] is False


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
    assert tuple(summary["default_params"]) == LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS


def test_lightgbm_dependency_smoke_has_only_expected_top_level_keys() -> None:
    summary = run_lightgbm_dependency_smoke()

    assert tuple(summary) == LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS


def test_lightgbm_dependency_smoke_summary_validator_accepts_valid_summary() -> None:
    summary = _valid_summary(installed=False)

    validated = validate_lightgbm_dependency_smoke_summary(summary)

    assert validated is summary
    assert validated == _valid_summary(installed=False)


def test_lightgbm_dependency_smoke_summary_validator_rejects_non_dict() -> None:
    with pytest.raises(TypeError, match="must be a dict"):
        validate_lightgbm_dependency_smoke_summary(["not", "a", "dict"])


def test_lightgbm_dependency_smoke_summary_validator_rejects_missing_top_level_key() -> None:
    summary = _valid_summary(installed=False)
    summary.pop("message")

    with pytest.raises(ValueError, match="missing=\\['message'\\]"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_summary_validator_rejects_extra_top_level_key() -> None:
    summary = _valid_summary(installed=False)
    summary["unexpected"] = "value"

    with pytest.raises(ValueError, match="unknown=\\['unexpected'\\]"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_summary_validator_rejects_non_dict_default_params() -> None:
    summary = _valid_summary(installed=False)
    summary["default_params"] = ["objective"]

    with pytest.raises(ValueError, match="default_params must be a dict"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_summary_validator_rejects_missing_default_param_key() -> None:
    summary = _valid_summary(installed=False)
    summary["default_params"].pop("objective")

    with pytest.raises(ValueError, match="missing=\\['objective'\\]"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_summary_validator_rejects_extra_default_param_key() -> None:
    summary = _valid_summary(installed=False)
    summary["default_params"]["extra_param"] = 1

    with pytest.raises(ValueError, match="unknown=\\['extra_param'\\]"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_summary_validator_rejects_non_json_friendly_value() -> None:
    summary = _valid_summary(installed=False)
    summary["default_params"]["learning_rate"] = float("nan")

    with pytest.raises(ValueError, match="must be JSON-friendly"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_summary_validator_rejects_forbidden_nested_key() -> None:
    summary = _valid_summary(installed=False)
    summary["default_params"]["strategy"] = "not allowed"

    with pytest.raises(ValueError, match="forbidden keys: strategy"):
        validate_lightgbm_dependency_smoke_summary(summary)


def test_lightgbm_dependency_smoke_does_not_expose_decision_or_simulation_keys() -> None:
    summary = run_lightgbm_dependency_smoke()
    forbidden_keys = {
        *LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS,
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


def _valid_summary(*, installed: bool) -> dict[str, object]:
    return {
        "package_name": "lightgbm",
        "installed": installed,
        "message": "fake lightgbm dependency status",
        "default_params": asdict(make_default_lightgbm_regressor_params()),
        "default_model_name": "lightgbm_regressor",
        "default_method": "lightgbm_regressor",
        "fitting_enabled": False,
    }


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
