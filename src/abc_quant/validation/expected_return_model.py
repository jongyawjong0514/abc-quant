"""Train-only ridge baseline for shadow expected net-return estimates.

The model is deliberately small and transparent. Feature transforms are fitted
on the discovery split, the ridge penalty is selected on validation rows, and
an affine bias correction is fitted on the calibration split. Forward returns
are evaluator inputs only and are never inferred from feature column names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


_FORBIDDEN_FEATURE_TOKENS = (
    "forward",
    "future",
    "target",
    "label",
    "net_return",
    "d5_adjusted_return",
    "exit_",
)


@dataclass(frozen=True)
class RidgeTransform:
    """Discovery-only feature transform."""

    feature_names: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray


@dataclass(frozen=True)
class RidgeValidationScore:
    """Validation loss for one predeclared penalty."""

    l2_penalty: float
    mse: float
    mae: float


@dataclass(frozen=True)
class ExpectedReturnModel:
    """Ridge return model with calibration-only affine correction."""

    transform: RidgeTransform
    intercept: float
    coefficients: np.ndarray
    l2_penalty: float
    calibration_intercept: float
    calibration_slope: float
    validation_scores: tuple[RidgeValidationScore, ...]


def fit_expected_return_model(
    discovery_features: pd.DataFrame,
    discovery_returns: Sequence[float] | pd.Series | np.ndarray,
    validation_features: pd.DataFrame,
    validation_returns: Sequence[float] | pd.Series | np.ndarray,
    calibration_features: pd.DataFrame,
    calibration_returns: Sequence[float] | pd.Series | np.ndarray,
    *,
    feature_names: Sequence[str],
    l2_grid: Sequence[float] = (0.1, 1.0, 10.0, 100.0),
) -> ExpectedReturnModel:
    """Fit discovery, select on validation, and bias-correct on calibration."""

    names = _validate_feature_names(discovery_features, feature_names)
    transform = _fit_transform(discovery_features, names)
    discovery_x = _transform(discovery_features, transform)
    validation_x = _transform(validation_features, transform)
    calibration_x = _transform(calibration_features, transform)
    discovery_y = _finite_vector(
        discovery_returns, "discovery_returns", len(discovery_x)
    )
    validation_y = _finite_vector(
        validation_returns, "validation_returns", len(validation_x)
    )
    calibration_y = _finite_vector(
        calibration_returns, "calibration_returns", len(calibration_x)
    )
    penalties = _validate_l2_grid(l2_grid)

    candidates: list[tuple[float, float, np.ndarray, RidgeValidationScore]] = []
    for penalty in penalties:
        intercept, coefficients = _fit_ridge(discovery_x, discovery_y, penalty)
        prediction = intercept + validation_x @ coefficients
        residual = validation_y - prediction
        candidates.append(
            (
                penalty,
                intercept,
                coefficients,
                RidgeValidationScore(
                    l2_penalty=penalty,
                    mse=float(np.mean(np.square(residual))),
                    mae=float(np.mean(np.abs(residual))),
                ),
            )
        )
    penalty, intercept, coefficients, _score = min(
        candidates,
        key=lambda item: (item[3].mse, item[3].mae, item[0]),
    )
    calibration_prediction = intercept + calibration_x @ coefficients
    calibration_intercept, calibration_slope = _fit_affine_calibration(
        calibration_prediction, calibration_y
    )
    return ExpectedReturnModel(
        transform=transform,
        intercept=float(intercept),
        coefficients=np.asarray(coefficients, dtype=float).copy(),
        l2_penalty=float(penalty),
        calibration_intercept=float(calibration_intercept),
        calibration_slope=float(calibration_slope),
        validation_scores=tuple(item[3] for item in candidates),
    )


def predict_expected_return(
    model: ExpectedReturnModel, features: pd.DataFrame
) -> np.ndarray:
    """Predict calibrated expected net return in the target's original unit."""

    if not isinstance(model, ExpectedReturnModel):
        raise TypeError("model must be an ExpectedReturnModel")
    matrix = _transform(features, model.transform)
    coefficients = np.asarray(model.coefficients, dtype=float)
    if coefficients.shape != (matrix.shape[1],):
        raise ValueError("feature count does not match model coefficients")
    raw = float(model.intercept) + matrix @ coefficients
    prediction = float(model.calibration_intercept) + float(
        model.calibration_slope
    ) * raw
    if np.any(~np.isfinite(prediction)):
        raise ValueError("expected-return predictions must be finite")
    return np.asarray(prediction, dtype=float)


def evaluate_expected_return(
    actual_returns: Sequence[float] | pd.Series | np.ndarray,
    predicted_returns: Sequence[float] | pd.Series | np.ndarray,
) -> dict[str, float | int]:
    """Return transparent holdout diagnostics for the regression sidecar."""

    predicted = _finite_vector(
        predicted_returns, "predicted_returns", len(predicted_returns)
    )
    actual = _finite_vector(actual_returns, "actual_returns", len(predicted))
    residual = actual - predicted
    if len(actual) > 1 and np.std(actual) > 0 and np.std(predicted) > 0:
        correlation = float(np.corrcoef(actual, predicted)[0, 1])
    else:
        correlation = float("nan")
    return {
        "rows": int(len(actual)),
        "mse": float(np.mean(np.square(residual))),
        "mae": float(np.mean(np.abs(residual))),
        "mean_actual": float(np.mean(actual)),
        "mean_predicted": float(np.mean(predicted)),
        "mean_bias": float(np.mean(predicted - actual)),
        "correlation": correlation,
    }


def _fit_transform(frame: pd.DataFrame, names: tuple[str, ...]) -> RidgeTransform:
    matrix = _numeric_matrix(frame, names)
    if len(matrix) == 0:
        raise ValueError("discovery_features must contain at least one row")
    medians = np.empty(matrix.shape[1], dtype=float)
    for index in range(matrix.shape[1]):
        finite = matrix[np.isfinite(matrix[:, index]), index]
        if finite.size == 0:
            raise ValueError(f"feature has no finite discovery values: {names[index]}")
        medians[index] = float(np.median(finite))
    filled = np.where(np.isfinite(matrix), matrix, medians)
    means = filled.mean(axis=0)
    scales = filled.std(axis=0, ddof=0)
    scales = np.where(scales > 1e-12, scales, 1.0)
    return RidgeTransform(names, medians, means, scales)


def _transform(frame: pd.DataFrame, transform: RidgeTransform) -> np.ndarray:
    names = _validate_feature_names(frame, transform.feature_names)
    matrix = _numeric_matrix(frame, names)
    filled = np.where(np.isfinite(matrix), matrix, transform.medians)
    output = (filled - transform.means) / transform.scales
    if np.any(~np.isfinite(output)):
        raise ValueError("transformed features must be finite")
    return np.asarray(output, dtype=float)


def _fit_ridge(
    matrix: np.ndarray, target: np.ndarray, penalty: float
) -> tuple[float, np.ndarray]:
    means = matrix.mean(axis=0)
    target_mean = float(target.mean())
    centered_x = matrix - means
    centered_y = target - target_mean
    gram = centered_x.T @ centered_x + penalty * np.eye(matrix.shape[1])
    coefficients = np.linalg.solve(gram, centered_x.T @ centered_y)
    intercept = target_mean - float(means @ coefficients)
    return intercept, coefficients


def _fit_affine_calibration(
    prediction: np.ndarray, target: np.ndarray
) -> tuple[float, float]:
    if len(prediction) == 0:
        raise ValueError("calibration split must contain at least one row")
    design = np.column_stack([np.ones(len(prediction)), prediction])
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    if np.any(~np.isfinite(coefficients)):
        raise ValueError("calibration coefficients must be finite")
    return float(coefficients[0]), float(coefficients[1])


def _validate_feature_names(
    frame: pd.DataFrame, feature_names: Sequence[str]
) -> tuple[str, ...]:
    names = tuple(str(value) for value in feature_names)
    if not names or len(names) != len(set(names)):
        raise ValueError("feature_names must be non-empty and unique")
    forbidden = [
        name
        for name in names
        if any(token in name.lower() for token in _FORBIDDEN_FEATURE_TOKENS)
    ]
    if forbidden:
        raise ValueError(f"outcome-like columns cannot be model features: {forbidden}")
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise ValueError(f"feature frame missing columns: {missing}")
    return names


def _numeric_matrix(frame: pd.DataFrame, names: tuple[str, ...]) -> np.ndarray:
    return frame.loc[:, list(names)].apply(pd.to_numeric, errors="coerce").to_numpy(float)


def _finite_vector(
    values: Sequence[float] | pd.Series | np.ndarray,
    name: str,
    expected_length: int,
) -> np.ndarray:
    output = np.asarray(values, dtype=float).reshape(-1)
    if len(output) != expected_length:
        raise ValueError(f"{name} length does not match feature rows")
    if len(output) == 0 or np.any(~np.isfinite(output)):
        raise ValueError(f"{name} must be non-empty and finite")
    return output


def _validate_l2_grid(values: Sequence[float]) -> tuple[float, ...]:
    output = tuple(float(value) for value in values)
    if not output or any(not np.isfinite(value) or value < 0 for value in output):
        raise ValueError("l2_grid must contain finite non-negative values")
    return output


__all__ = [
    "ExpectedReturnModel",
    "RidgeTransform",
    "RidgeValidationScore",
    "evaluate_expected_return",
    "fit_expected_return_model",
    "predict_expected_return",
]
