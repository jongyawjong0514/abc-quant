import importlib
from dataclasses import asdict

import pytest

import abc_quant.pipeline as pipeline
import abc_quant.pipeline.lightgbm_diagnostics as lightgbm_diagnostics
from abc_quant.models import (
    LightGBMDependencyStatus,
    make_default_lightgbm_regressor_params,
)


def test_pipeline_reexports_lightgbm_dependency_smoke_contract_symbols() -> None:
    assert (
        pipeline.LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS
        is lightgbm_diagnostics.LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS
    )
    assert (
        pipeline.LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS
        is lightgbm_diagnostics.LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS
    )
    assert (
        pipeline.LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS
        is lightgbm_diagnostics.LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS
    )
    assert (
        pipeline.validate_lightgbm_dependency_smoke_summary
        is lightgbm_diagnostics.validate_lightgbm_dependency_smoke_summary
    )


def test_pipeline_all_lists_lightgbm_dependency_smoke_contract_symbols() -> None:
    assert "LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS" in pipeline.__all__
    assert "LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS" in pipeline.__all__
    assert "LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS" in pipeline.__all__
    assert "validate_lightgbm_dependency_smoke_summary" in pipeline.__all__


def test_pipeline_exported_constants_match_current_summary_key_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lightgbm_diagnostics,
        "check_lightgbm_dependency",
        lambda: LightGBMDependencyStatus(
            package_name="lightgbm",
            installed=False,
            message="lightgbm missing for export test",
        ),
    )

    summary = pipeline.run_lightgbm_dependency_smoke()

    assert tuple(summary) == pipeline.LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS
    assert (
        tuple(summary["default_params"])
        == pipeline.LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS
    )
    assert summary["default_params"] == asdict(make_default_lightgbm_regressor_params())


def test_pipeline_exported_validator_accepts_valid_smoke_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lightgbm_diagnostics,
        "check_lightgbm_dependency",
        lambda: LightGBMDependencyStatus(
            package_name="lightgbm",
            installed=True,
            message="lightgbm available for export test",
        ),
    )
    summary = pipeline.run_lightgbm_dependency_smoke()

    validated = pipeline.validate_lightgbm_dependency_smoke_summary(summary)

    assert validated is summary
    assert validated["installed"] is True


def test_pipeline_exported_validator_rejects_extra_top_level_key() -> None:
    summary = _valid_summary()
    summary["unexpected"] = "not part of the public contract"

    with pytest.raises(ValueError, match="unknown=\\['unexpected'\\]"):
        pipeline.validate_lightgbm_dependency_smoke_summary(summary)


def test_importing_pipeline_does_not_require_real_lightgbm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported_names: list[str] = []
    original_import_module = importlib.import_module

    def guarded_import_module(name: str, package: str | None = None) -> object:
        imported_names.append(name)
        if name == "lightgbm":
            raise AssertionError("abc_quant.pipeline import must not import LightGBM")
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", guarded_import_module)

    imported_pipeline = importlib.import_module("abc_quant.pipeline")

    assert imported_pipeline is pipeline
    assert "lightgbm" not in imported_names


def _valid_summary() -> dict[str, object]:
    return {
        "package_name": "lightgbm",
        "installed": False,
        "message": "fake lightgbm dependency status",
        "default_params": asdict(make_default_lightgbm_regressor_params()),
        "default_model_name": "lightgbm_regressor",
        "default_method": "lightgbm_regressor",
        "fitting_enabled": False,
    }
