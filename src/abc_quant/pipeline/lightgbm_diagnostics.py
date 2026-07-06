"""Deterministic LightGBM dependency smoke diagnostics."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Final

from abc_quant.models.lightgbm import (
    check_lightgbm_dependency,
    make_default_lightgbm_regressor_params,
)

DEFAULT_LIGHTGBM_DIAGNOSTIC_MODEL_NAME: Final[str] = "lightgbm_regressor"
DEFAULT_LIGHTGBM_DIAGNOSTIC_METHOD: Final[str] = "lightgbm_regressor"


def run_lightgbm_dependency_smoke() -> dict[str, Any]:
    """Return JSON-friendly optional LightGBM dependency diagnostics.

    This default smoke path intentionally checks dependency status only. It
    does not import the optional package through `require_lightgbm()`, fit a
    model, search parameters, select models, create strategy outputs, define
    allocation logic, build performance curves, or run simulation engines.
    """
    dependency_status = check_lightgbm_dependency()
    default_params = make_default_lightgbm_regressor_params()
    return {
        "package_name": dependency_status.package_name,
        "installed": bool(dependency_status.installed),
        "message": dependency_status.message,
        "default_params": asdict(default_params),
        "default_model_name": DEFAULT_LIGHTGBM_DIAGNOSTIC_MODEL_NAME,
        "default_method": DEFAULT_LIGHTGBM_DIAGNOSTIC_METHOD,
        "fitting_enabled": False,
    }
