"""Optional LightGBM dependency guard and parameter contracts."""

from __future__ import annotations

import importlib
import importlib.util
import math
from dataclasses import dataclass
from types import ModuleType
from typing import Final


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
