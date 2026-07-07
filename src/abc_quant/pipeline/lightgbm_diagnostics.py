"""Deterministic LightGBM dependency smoke diagnostics."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Final

from abc_quant.models.lightgbm import (
    check_lightgbm_dependency,
    make_default_lightgbm_regressor_params,
)

DEFAULT_LIGHTGBM_DIAGNOSTIC_MODEL_NAME: Final[str] = "lightgbm_regressor"
DEFAULT_LIGHTGBM_DIAGNOSTIC_METHOD: Final[str] = "lightgbm_regressor"
LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS: Final[tuple[str, ...]] = (
    "package_name",
    "installed",
    "message",
    "default_params",
    "default_model_name",
    "default_method",
    "fitting_enabled",
)
LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS: Final[tuple[str, ...]] = (
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
)
LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS: Final[tuple[str, ...]] = (
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
)


def run_lightgbm_dependency_smoke() -> dict[str, Any]:
    """Return JSON-friendly optional LightGBM dependency diagnostics.

    This default smoke path intentionally checks dependency status only. It
    does not import the optional package through `require_lightgbm()`, fit a
    model, search parameters, select models, create strategy outputs, define
    allocation logic, build performance curves, or run simulation engines.
    """
    dependency_status = check_lightgbm_dependency()
    default_params = make_default_lightgbm_regressor_params()
    summary = {
        "package_name": dependency_status.package_name,
        "installed": bool(dependency_status.installed),
        "message": dependency_status.message,
        "default_params": asdict(default_params),
        "default_model_name": DEFAULT_LIGHTGBM_DIAGNOSTIC_MODEL_NAME,
        "default_method": DEFAULT_LIGHTGBM_DIAGNOSTIC_METHOD,
        "fitting_enabled": False,
    }
    return validate_lightgbm_dependency_smoke_summary(summary)


def validate_lightgbm_dependency_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the LightGBM dependency smoke diagnostics summary shape.

    The function returns the original summary object unchanged when valid.
    """
    if not isinstance(summary, dict):
        raise TypeError("LightGBM dependency smoke summary must be a dict")

    forbidden = sorted(
        set(LIGHTGBM_DEPENDENCY_SMOKE_FORBIDDEN_KEYS)
        & _collect_nested_keys(summary)
    )
    if forbidden:
        raise ValueError(
            "LightGBM dependency smoke summary contains forbidden keys: "
            + ", ".join(forbidden)
        )

    _validate_key_tuple(
        "LightGBM dependency smoke summary",
        actual_keys=summary.keys(),
        expected_keys=LIGHTGBM_DEPENDENCY_SMOKE_SUMMARY_KEYS,
    )

    default_params = summary["default_params"]
    if not isinstance(default_params, dict):
        raise ValueError(
            "LightGBM dependency smoke summary default_params must be a dict"
        )
    _validate_key_tuple(
        "LightGBM dependency smoke summary default_params",
        actual_keys=default_params.keys(),
        expected_keys=LIGHTGBM_DEPENDENCY_SMOKE_DEFAULT_PARAM_KEYS,
    )

    try:
        json.dumps(summary, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "LightGBM dependency smoke summary must be JSON-friendly"
        ) from exc

    return summary


def _validate_key_tuple(
    context: str,
    *,
    actual_keys: object,
    expected_keys: tuple[str, ...],
) -> None:
    expected = set(expected_keys)
    actual = {str(key) for key in actual_keys}
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{context} keys mismatch: missing={missing}; unknown={unknown}"
        )


def _collect_nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_collect_nested_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_nested_keys(item))
        return keys
    return set()
