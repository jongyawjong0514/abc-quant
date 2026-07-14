"""Leakage-resistant probability helpers for the D-10 probability challenger.

The module intentionally depends only on NumPy and pandas.  Feature transforms
are fitted from an explicitly supplied training frame, model selection observes
only an explicitly supplied validation split, and Platt calibration observes
only an explicitly supplied calibration split.  Forward returns and labels are
accepted only by evaluator functions and are never inferred from feature frames.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


_PROBABILITY_EPSILON = 1e-12
_SCALE_EPSILON = 1e-12


@dataclass(frozen=True)
class FeatureTransform:
    """Train-only median imputation and standardization parameters."""

    feature_names: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray


@dataclass(frozen=True)
class LogisticModel:
    """L2 logistic-regression coefficients fitted by Newton/IRLS updates."""

    intercept: float
    coefficients: np.ndarray
    l2_penalty: float
    converged: bool
    iterations: int


@dataclass(frozen=True)
class LambdaValidationScore:
    """Validation loss for one candidate L2 penalty."""

    l2_penalty: float
    brier: float
    logloss: float
    converged: bool
    iterations: int


@dataclass(frozen=True)
class L2SelectionResult:
    """Train-fitted transform/model selected using validation loss only."""

    transform: FeatureTransform
    model: LogisticModel
    selection_metric: str
    validation_scores: tuple[LambdaValidationScore, ...]


@dataclass(frozen=True)
class PlattCalibrator:
    """One-dimensional logistic calibrator over uncalibrated log-odds."""

    intercept: float
    slope: float
    converged: bool
    iterations: int


@dataclass(frozen=True)
class ProbabilityChallenger:
    """Fitted D-10 probability challenger and its split-specific artifacts."""

    transform: FeatureTransform
    logistic_model: LogisticModel
    platt_calibrator: PlattCalibrator
    selection_metric: str
    validation_scores: tuple[LambdaValidationScore, ...]


@dataclass(frozen=True)
class BinaryRuleCalibrator:
    """Smoothed empirical probabilities for a binary rule's two bins."""

    false_probability: float
    true_probability: float
    false_count: int
    true_count: int
    smoothing_alpha: float


@dataclass(frozen=True)
class DateBlockBootstrapResult:
    """Paired challenger-minus-baseline metric delta by resampled date blocks."""

    metric: str
    observed_delta: float
    bootstrap_mean_delta: float
    confidence_lower: float
    confidence_upper: float
    two_sided_p_value: float
    n_bootstrap: int
    effective_bootstrap: int
    block_length: int
    tail_loss_threshold: float
    samples: np.ndarray


@dataclass(frozen=True)
class BenjaminiHochbergResult:
    """Benjamini-Hochberg false-discovery-rate adjustment result."""

    adjusted_p_values: np.ndarray
    rejected: np.ndarray
    critical_p_value: float | None
    alpha: float


def fit_feature_transform(
    train_features: pd.DataFrame,
    feature_names: Sequence[str],
) -> FeatureTransform:
    """Fit median fill and population standardization on training rows only."""
    names = _validate_feature_names(train_features, feature_names)
    matrix = _numeric_feature_matrix(train_features, names)
    if matrix.shape[0] == 0:
        raise ValueError("train_features must contain at least one row")

    medians = np.empty(matrix.shape[1], dtype=float)
    for column_index in range(matrix.shape[1]):
        finite = matrix[np.isfinite(matrix[:, column_index]), column_index]
        medians[column_index] = float(np.median(finite)) if finite.size else 0.0

    filled = np.where(np.isfinite(matrix), matrix, medians)
    means = filled.mean(axis=0)
    scales = filled.std(axis=0, ddof=0)
    scales = np.where(np.isfinite(scales) & (scales > _SCALE_EPSILON), scales, 1.0)
    return FeatureTransform(
        feature_names=names,
        medians=medians.copy(),
        means=np.asarray(means, dtype=float).copy(),
        scales=np.asarray(scales, dtype=float).copy(),
    )


def transform_features(
    features: pd.DataFrame,
    transform: FeatureTransform,
) -> np.ndarray:
    """Apply a previously fitted transform without inspecting other columns."""
    if not isinstance(transform, FeatureTransform):
        raise TypeError("transform must be a FeatureTransform")
    names = _validate_feature_names(features, transform.feature_names)
    matrix = _numeric_feature_matrix(features, names)
    expected = len(names)
    for values, field_name in (
        (transform.medians, "medians"),
        (transform.means, "means"),
        (transform.scales, "scales"),
    ):
        if np.asarray(values).shape != (expected,):
            raise ValueError(f"transform {field_name} length does not match feature_names")
    if np.any(~np.isfinite(transform.scales)) or np.any(transform.scales <= 0.0):
        raise ValueError("transform scales must be finite and positive")

    filled = np.where(np.isfinite(matrix), matrix, transform.medians)
    transformed = (filled - transform.means) / transform.scales
    if np.any(~np.isfinite(transformed)):
        raise ValueError("transformed features must be finite")
    return np.asarray(transformed, dtype=float)


def fit_l2_logistic(
    features: np.ndarray | pd.DataFrame,
    labels: Sequence[float] | np.ndarray | pd.Series,
    *,
    l2_penalty: float = 1.0,
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> LogisticModel:
    """Fit logistic regression with an unregularized intercept via Newton/IRLS."""
    matrix = _as_finite_matrix(features, "features")
    targets = _as_binary_vector(labels, "labels", expected_length=matrix.shape[0])
    _validate_optimizer_arguments(l2_penalty, max_iterations, tolerance)
    return _fit_logistic_newton(
        matrix,
        targets,
        l2_penalty=float(l2_penalty),
        max_iterations=max_iterations,
        tolerance=tolerance,
    )


def predict_logistic_proba(
    model: LogisticModel,
    features: np.ndarray | pd.DataFrame,
) -> np.ndarray:
    """Predict positive-class probabilities from a fitted logistic model."""
    if not isinstance(model, LogisticModel):
        raise TypeError("model must be a LogisticModel")
    matrix = _as_finite_matrix(features, "features")
    coefficients = np.asarray(model.coefficients, dtype=float)
    if coefficients.shape != (matrix.shape[1],):
        raise ValueError("feature count does not match logistic coefficients")
    if not np.isfinite(model.intercept) or np.any(~np.isfinite(coefficients)):
        raise ValueError("logistic model parameters must be finite")
    return _stable_sigmoid(model.intercept + matrix @ coefficients)


def select_l2_by_validation(
    train_features: pd.DataFrame,
    train_labels: Sequence[float] | np.ndarray | pd.Series,
    validation_features: pd.DataFrame,
    validation_labels: Sequence[float] | np.ndarray | pd.Series,
    *,
    feature_names: Sequence[str],
    l2_grid: Sequence[float] = (0.01, 0.1, 1.0, 10.0),
    selection_metric: str = "brier",
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> L2SelectionResult:
    """Select a train-fitted model using only the supplied validation split."""
    metric = _validate_selection_metric(selection_metric)
    penalties = _validate_l2_grid(l2_grid)
    transform = fit_feature_transform(train_features, feature_names)
    train_matrix = transform_features(train_features, transform)
    validation_matrix = transform_features(validation_features, transform)
    train_targets = _as_binary_vector(
        train_labels,
        "train_labels",
        expected_length=train_matrix.shape[0],
    )
    validation_targets = _as_binary_vector(
        validation_labels,
        "validation_labels",
        expected_length=validation_matrix.shape[0],
    )
    if validation_targets.size == 0:
        raise ValueError("validation split must contain at least one row")

    candidates: list[tuple[LogisticModel, LambdaValidationScore]] = []
    for penalty in penalties:
        model = fit_l2_logistic(
            train_matrix,
            train_targets,
            l2_penalty=penalty,
            max_iterations=max_iterations,
            tolerance=tolerance,
        )
        probability = predict_logistic_proba(model, validation_matrix)
        candidates.append(
            (
                model,
                LambdaValidationScore(
                    l2_penalty=penalty,
                    brier=brier_score(validation_targets, probability),
                    logloss=binary_log_loss(validation_targets, probability),
                    converged=model.converged,
                    iterations=model.iterations,
                ),
            )
        )

    # Prefer the more regularized model when validation scores are numerically tied.
    chosen_model, _ = min(
        candidates,
        key=lambda candidate: (
            getattr(candidate[1], metric),
            -candidate[1].l2_penalty,
        ),
    )
    return L2SelectionResult(
        transform=transform,
        model=chosen_model,
        selection_metric=metric,
        validation_scores=tuple(score for _, score in candidates),
    )


def fit_platt_calibrator(
    uncalibrated_probabilities: Sequence[float] | np.ndarray | pd.Series,
    calibration_labels: Sequence[float] | np.ndarray | pd.Series,
    *,
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> PlattCalibrator:
    """Fit Platt scaling using only the explicitly supplied calibration split."""
    probability = _as_probability_vector(
        uncalibrated_probabilities,
        "uncalibrated_probabilities",
    )
    labels = _as_binary_vector(
        calibration_labels,
        "calibration_labels",
        expected_length=probability.size,
    )
    if probability.size == 0:
        raise ValueError("calibration split must contain at least one row")
    _validate_optimizer_arguments(1e-8, max_iterations, tolerance)

    positive_count = int(labels.sum())
    negative_count = int(labels.size - positive_count)
    high_target = (positive_count + 1.0) / (positive_count + 2.0)
    low_target = 1.0 / (negative_count + 2.0)
    smoothed_targets = np.where(labels == 1.0, high_target, low_target)
    clipped = np.clip(probability, _PROBABILITY_EPSILON, 1.0 - _PROBABILITY_EPSILON)
    log_odds = np.log(clipped) - np.log1p(-clipped)
    model = _fit_logistic_newton(
        log_odds[:, None],
        smoothed_targets,
        l2_penalty=1e-8,
        max_iterations=max_iterations,
        tolerance=tolerance,
    )
    return PlattCalibrator(
        intercept=model.intercept,
        slope=float(model.coefficients[0]),
        converged=model.converged,
        iterations=model.iterations,
    )


def apply_platt_calibration(
    calibrator: PlattCalibrator,
    uncalibrated_probabilities: Sequence[float] | np.ndarray | pd.Series,
) -> np.ndarray:
    """Apply a fitted Platt calibrator to uncalibrated probabilities."""
    if not isinstance(calibrator, PlattCalibrator):
        raise TypeError("calibrator must be a PlattCalibrator")
    probability = _as_probability_vector(
        uncalibrated_probabilities,
        "uncalibrated_probabilities",
    )
    clipped = np.clip(probability, _PROBABILITY_EPSILON, 1.0 - _PROBABILITY_EPSILON)
    log_odds = np.log(clipped) - np.log1p(-clipped)
    return _stable_sigmoid(calibrator.intercept + calibrator.slope * log_odds)


def fit_probability_challenger(
    train_features: pd.DataFrame,
    train_labels: Sequence[float] | np.ndarray | pd.Series,
    validation_features: pd.DataFrame,
    validation_labels: Sequence[float] | np.ndarray | pd.Series,
    calibration_features: pd.DataFrame,
    calibration_labels: Sequence[float] | np.ndarray | pd.Series,
    *,
    feature_names: Sequence[str],
    l2_grid: Sequence[float] = (0.01, 0.1, 1.0, 10.0),
    selection_metric: str = "brier",
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> ProbabilityChallenger:
    """Fit transform, select L2 on validation, then calibrate on calibration rows."""
    selection = select_l2_by_validation(
        train_features,
        train_labels,
        validation_features,
        validation_labels,
        feature_names=feature_names,
        l2_grid=l2_grid,
        selection_metric=selection_metric,
        max_iterations=max_iterations,
        tolerance=tolerance,
    )
    calibration_matrix = transform_features(calibration_features, selection.transform)
    calibration_probability = predict_logistic_proba(selection.model, calibration_matrix)
    calibrator = fit_platt_calibrator(
        calibration_probability,
        calibration_labels,
        max_iterations=max_iterations,
        tolerance=tolerance,
    )
    return ProbabilityChallenger(
        transform=selection.transform,
        logistic_model=selection.model,
        platt_calibrator=calibrator,
        selection_metric=selection.selection_metric,
        validation_scores=selection.validation_scores,
    )


def predict_probability_challenger(
    challenger: ProbabilityChallenger,
    features: pd.DataFrame,
) -> np.ndarray:
    """Predict calibrated probabilities using only named feature columns."""
    if not isinstance(challenger, ProbabilityChallenger):
        raise TypeError("challenger must be a ProbabilityChallenger")
    matrix = transform_features(features, challenger.transform)
    raw_probability = predict_logistic_proba(challenger.logistic_model, matrix)
    return apply_platt_calibration(challenger.platt_calibrator, raw_probability)


def brier_score(
    labels: Sequence[float] | np.ndarray | pd.Series,
    probabilities: Sequence[float] | np.ndarray | pd.Series,
) -> float:
    """Return mean squared probability error."""
    probability = _as_probability_vector(probabilities, "probabilities")
    targets = _as_binary_vector(labels, "labels", expected_length=probability.size)
    if probability.size == 0:
        return float("nan")
    return float(np.mean((probability - targets) ** 2))


def binary_log_loss(
    labels: Sequence[float] | np.ndarray | pd.Series,
    probabilities: Sequence[float] | np.ndarray | pd.Series,
) -> float:
    """Return numerically stable binary cross-entropy."""
    probability = _as_probability_vector(probabilities, "probabilities")
    targets = _as_binary_vector(labels, "labels", expected_length=probability.size)
    if probability.size == 0:
        return float("nan")
    clipped = np.clip(probability, _PROBABILITY_EPSILON, 1.0 - _PROBABILITY_EPSILON)
    return float(-np.mean(targets * np.log(clipped) + (1.0 - targets) * np.log1p(-clipped)))


def expected_calibration_error(
    labels: Sequence[float] | np.ndarray | pd.Series,
    probabilities: Sequence[float] | np.ndarray | pd.Series,
    *,
    bin_count: int = 10,
) -> float:
    """Return equal-width expected calibration error."""
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count <= 0:
        raise ValueError("bin_count must be a positive integer")
    probability = _as_probability_vector(probabilities, "probabilities")
    targets = _as_binary_vector(labels, "labels", expected_length=probability.size)
    if probability.size == 0:
        return float("nan")

    bin_index = np.minimum((probability * bin_count).astype(int), bin_count - 1)
    error = 0.0
    for index in range(bin_count):
        mask = bin_index == index
        if np.any(mask):
            error += float(mask.mean()) * abs(
                float(targets[mask].mean()) - float(probability[mask].mean())
            )
    return float(error)


def evaluate_probability_predictions(
    labels: Sequence[float] | np.ndarray | pd.Series,
    probabilities: Sequence[float] | np.ndarray | pd.Series,
    *,
    threshold: float = 0.5,
    net_returns: Sequence[float] | np.ndarray | pd.Series | None = None,
    dates: Sequence[object] | np.ndarray | pd.Series | None = None,
    all_dates: Sequence[object] | np.ndarray | pd.Series | None = None,
    ece_bin_count: int = 10,
    tail_loss_threshold: float = -0.05,
) -> dict[str, float | int]:
    """Evaluate calibration, classification, return, and coverage diagnostics."""
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between zero and one")
    if not np.isfinite(tail_loss_threshold):
        raise ValueError("tail_loss_threshold must be finite")

    raw_probability = _as_float_vector(probabilities, "probabilities")
    targets = _as_binary_vector(labels, "labels", expected_length=raw_probability.size)
    valid_probability = np.isfinite(raw_probability) & (raw_probability >= 0.0) & (
        raw_probability <= 1.0
    )
    valid_count = int(valid_probability.sum())
    observation_count = int(raw_probability.size)
    valid_targets = targets[valid_probability]
    valid_probabilities = raw_probability[valid_probability]
    selected_valid = valid_probabilities >= threshold
    selected = np.zeros(observation_count, dtype=bool)
    selected[np.flatnonzero(valid_probability)] = selected_valid

    predicted = selected_valid.astype(float)
    true_positive = int(np.sum((predicted == 1.0) & (valid_targets == 1.0)))
    false_positive = int(np.sum((predicted == 1.0) & (valid_targets == 0.0)))
    true_negative = int(np.sum((predicted == 0.0) & (valid_targets == 0.0)))
    false_negative = int(np.sum((predicted == 0.0) & (valid_targets == 1.0)))
    positive_count = true_positive + false_negative
    negative_count = true_negative + false_positive
    selected_count = true_positive + false_positive
    precision = _safe_ratio(true_positive, selected_count)
    recall = _safe_ratio(true_positive, positive_count)
    specificity = _safe_ratio(true_negative, negative_count)
    f1 = _safe_ratio(2.0 * precision * recall, precision + recall)
    balanced_accuracy = (
        float((recall + specificity) / 2.0)
        if np.isfinite(recall) and np.isfinite(specificity)
        else float("nan")
    )
    prevalence = _safe_ratio(positive_count, valid_count)
    lift = _safe_ratio(precision, prevalence)

    mean_net_return = float("nan")
    median_net_return = float("nan")
    loss_rate = float("nan")
    tail_loss_rate = float("nan")
    cvar_5 = float("nan")
    selected_return_count = 0
    if net_returns is not None:
        returns = _as_float_vector(net_returns, "net_returns")
        if returns.size != observation_count:
            raise ValueError("net_returns length does not match probabilities")
        selected_returns = returns[selected & np.isfinite(returns)]
        selected_return_count = int(selected_returns.size)
        if selected_returns.size:
            mean_net_return = float(selected_returns.mean())
            median_net_return = float(np.median(selected_returns))
            loss_rate = float(np.mean(selected_returns < 0.0))
            tail_loss_rate = float(np.mean(selected_returns <= tail_loss_threshold))
            tail_count = max(1, int(np.ceil(0.05 * selected_returns.size)))
            cvar_5 = float(np.sort(selected_returns)[:tail_count].mean())

    date_count = 0
    selected_date_count = 0
    empty_date_count = 0
    if dates is not None:
        date_values = _as_object_vector(dates, "dates", expected_length=observation_count)
        if pd.isna(date_values).any():
            raise ValueError("dates must not contain missing values")
        observed_dates = list(pd.unique(date_values))
        date_universe = (
            observed_dates
            if all_dates is None
            else list(pd.unique(_as_object_vector(all_dates, "all_dates")))
        )
        if pd.isna(np.asarray(date_universe, dtype=object)).any():
            raise ValueError("all_dates must not contain missing values")
        observed_set = set(observed_dates)
        missing_from_rows = [date for date in date_universe if date not in observed_set]
        selected_by_date = {
            date for date, is_selected in zip(date_values, selected, strict=True) if is_selected
        }
        date_count = len(date_universe)
        selected_date_count = sum(date in selected_by_date for date in date_universe)
        empty_date_count = len(missing_from_rows) + sum(
            date not in selected_by_date for date in observed_dates if date in set(date_universe)
        )

    return {
        "observation_count": observation_count,
        "valid_probability_count": valid_count,
        "selected_count": selected_count,
        "brier": brier_score(valid_targets, valid_probabilities),
        "logloss": binary_log_loss(valid_targets, valid_probabilities),
        "ece": expected_calibration_error(
            valid_targets,
            valid_probabilities,
            bin_count=ece_bin_count,
        ),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_accuracy": balanced_accuracy,
        "lift": lift,
        "mean_net_return": mean_net_return,
        "median_net_return": median_net_return,
        "loss_rate": loss_rate,
        "tail_loss_rate": tail_loss_rate,
        "cvar_5": cvar_5,
        "selected_return_count": selected_return_count,
        "coverage": _safe_ratio(selected_count, valid_count),
        "valid_probability_coverage": _safe_ratio(valid_count, observation_count),
        "date_count": date_count,
        "selected_date_count": selected_date_count,
        "empty_date_count": empty_date_count,
    }


def fit_binary_rule_calibrator(
    rule_values: Sequence[bool] | np.ndarray | pd.Series,
    labels: Sequence[float] | np.ndarray | pd.Series,
    *,
    smoothing_alpha: float = 1.0,
) -> BinaryRuleCalibrator:
    """Fit smoothed outcome rates independently for false and true rule bins."""
    rule = _as_binary_vector(rule_values, "rule_values")
    targets = _as_binary_vector(labels, "labels", expected_length=rule.size)
    if rule.size == 0:
        raise ValueError("binary-rule calibration split must contain at least one row")
    if not np.isfinite(smoothing_alpha) or smoothing_alpha <= 0.0:
        raise ValueError("smoothing_alpha must be finite and positive")

    false_mask = rule == 0.0
    true_mask = ~false_mask
    false_count = int(false_mask.sum())
    true_count = int(true_mask.sum())
    false_probability = (float(targets[false_mask].sum()) + smoothing_alpha) / (
        false_count + 2.0 * smoothing_alpha
    )
    true_probability = (float(targets[true_mask].sum()) + smoothing_alpha) / (
        true_count + 2.0 * smoothing_alpha
    )
    return BinaryRuleCalibrator(
        false_probability=float(false_probability),
        true_probability=float(true_probability),
        false_count=false_count,
        true_count=true_count,
        smoothing_alpha=float(smoothing_alpha),
    )


def predict_binary_rule_proba(
    calibrator: BinaryRuleCalibrator,
    rule_values: Sequence[bool] | np.ndarray | pd.Series,
) -> np.ndarray:
    """Map a binary rule to its fitted false/true-bin probability."""
    if not isinstance(calibrator, BinaryRuleCalibrator):
        raise TypeError("calibrator must be a BinaryRuleCalibrator")
    rule = _as_binary_vector(rule_values, "rule_values")
    return np.where(
        rule == 1.0,
        calibrator.true_probability,
        calibrator.false_probability,
    )


def daily_matched_count_top_k(
    dates: Sequence[object] | np.ndarray | pd.Series,
    challenger_scores: Sequence[float] | np.ndarray | pd.Series,
    reference_selected: Sequence[bool] | np.ndarray | pd.Series,
) -> np.ndarray:
    """Select challenger top-k per day where k equals reference selections that day."""
    scores = _as_float_vector(challenger_scores, "challenger_scores")
    date_values = _as_object_vector(dates, "dates", expected_length=scores.size)
    reference = _as_binary_vector(
        reference_selected,
        "reference_selected",
        expected_length=scores.size,
    ).astype(bool)
    if pd.isna(date_values).any():
        raise ValueError("dates must not contain missing values")

    selected = np.zeros(scores.size, dtype=bool)
    for date in pd.unique(date_values):
        positions = np.flatnonzero(date_values == date)
        required = int(reference[positions].sum())
        if required == 0:
            continue
        finite_positions = positions[np.isfinite(scores[positions])]
        if finite_positions.size < required:
            raise ValueError(f"not enough finite challenger scores to match count for date {date!r}")
        order = np.lexsort((finite_positions, -scores[finite_positions]))
        selected[finite_positions[order[:required]]] = True
    return selected


def date_block_bootstrap_paired_delta(
    dates: Sequence[object] | np.ndarray | pd.Series,
    labels: Sequence[float] | np.ndarray | pd.Series,
    challenger_probabilities: Sequence[float] | np.ndarray | pd.Series,
    baseline_probabilities: Sequence[float] | np.ndarray | pd.Series,
    *,
    metric: str = "brier",
    n_bootstrap: int = 1000,
    block_length: int = 1,
    confidence_level: float = 0.95,
    random_seed: int = 0,
    threshold: float = 0.5,
    tail_loss_threshold: float = -0.05,
    net_returns: Sequence[float] | np.ndarray | pd.Series | None = None,
) -> DateBlockBootstrapResult:
    """Bootstrap paired deltas using circular moving blocks of whole dates."""
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be a positive integer")
    if isinstance(block_length, bool) or not isinstance(block_length, int) or block_length <= 0:
        raise ValueError("block_length must be a positive integer")
    if not np.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between zero and one")
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between zero and one")
    if not np.isfinite(tail_loss_threshold):
        raise ValueError("tail_loss_threshold must be finite")
    metric_name = _validate_bootstrap_metric(metric)

    challenger = _as_probability_vector(challenger_probabilities, "challenger_probabilities")
    baseline = _as_probability_vector(
        baseline_probabilities,
        "baseline_probabilities",
        expected_length=challenger.size,
    )
    targets = _as_binary_vector(labels, "labels", expected_length=challenger.size)
    date_values = _as_object_vector(dates, "dates", expected_length=challenger.size)
    if challenger.size == 0:
        raise ValueError("bootstrap inputs must contain at least one row")
    if pd.isna(date_values).any():
        raise ValueError("dates must not contain missing values")
    returns = None
    if net_returns is not None:
        returns = _as_float_vector(net_returns, "net_returns")
        if returns.size != challenger.size or np.any(~np.isfinite(returns)):
            raise ValueError("net_returns must be finite and match probability length")

    unique_dates = pd.Index(pd.unique(date_values)).sort_values().to_numpy(dtype=object)
    date_positions = [np.flatnonzero(date_values == date) for date in unique_dates]
    observed_delta = _paired_metric_delta(
        metric_name,
        targets,
        challenger,
        baseline,
        threshold=threshold,
        tail_loss_threshold=tail_loss_threshold,
        net_returns=returns,
    )
    if not np.isfinite(observed_delta):
        raise ValueError("observed metric delta is undefined")

    rng = np.random.default_rng(random_seed)
    samples = np.full(n_bootstrap, np.nan, dtype=float)
    date_count = len(date_positions)
    block_count = int(np.ceil(date_count / block_length))
    block_offsets = np.arange(block_length, dtype=int)
    for iteration in range(n_bootstrap):
        block_starts = rng.integers(0, date_count, size=block_count)
        sampled_dates = (
            block_starts[:, np.newaxis] + block_offsets[np.newaxis, :]
        ) % date_count
        sampled_dates = sampled_dates.ravel()[:date_count]
        row_positions = np.concatenate([date_positions[index] for index in sampled_dates])
        sampled_returns = None if returns is None else returns[row_positions]
        samples[iteration] = _paired_metric_delta(
            metric_name,
            targets[row_positions],
            challenger[row_positions],
            baseline[row_positions],
            threshold=threshold,
            tail_loss_threshold=tail_loss_threshold,
            net_returns=sampled_returns,
        )

    finite_samples = samples[np.isfinite(samples)]
    if finite_samples.size == 0:
        raise ValueError("all bootstrap metric deltas are undefined")
    alpha = 1.0 - confidence_level
    lower, upper = np.quantile(finite_samples, [alpha / 2.0, 1.0 - alpha / 2.0])
    lower_tail = (np.sum(finite_samples <= 0.0) + 1.0) / (finite_samples.size + 1.0)
    upper_tail = (np.sum(finite_samples >= 0.0) + 1.0) / (finite_samples.size + 1.0)
    two_sided_p_value = min(1.0, 2.0 * min(lower_tail, upper_tail))
    return DateBlockBootstrapResult(
        metric=metric_name,
        observed_delta=float(observed_delta),
        bootstrap_mean_delta=float(finite_samples.mean()),
        confidence_lower=float(lower),
        confidence_upper=float(upper),
        two_sided_p_value=float(two_sided_p_value),
        n_bootstrap=n_bootstrap,
        effective_bootstrap=int(finite_samples.size),
        block_length=block_length,
        tail_loss_threshold=float(tail_loss_threshold),
        samples=samples,
    )


def benjamini_hochberg(
    p_values: Sequence[float] | np.ndarray | pd.Series,
    *,
    alpha: float = 0.05,
) -> BenjaminiHochbergResult:
    """Adjust p-values and return discoveries controlling FDR at ``alpha``."""
    if not np.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between zero and one")
    raw = _as_float_vector(p_values, "p_values")
    invalid = np.isfinite(raw) & ((raw < 0.0) | (raw > 1.0))
    if np.any(invalid) or np.any(np.isinf(raw)):
        raise ValueError("finite p_values must be between zero and one")
    valid_positions = np.flatnonzero(np.isfinite(raw))
    adjusted = np.full(raw.size, np.nan, dtype=float)
    rejected = np.zeros(raw.size, dtype=bool)
    if valid_positions.size == 0:
        return BenjaminiHochbergResult(adjusted, rejected, None, float(alpha))

    order_within_valid = np.argsort(raw[valid_positions], kind="mergesort")
    ordered_positions = valid_positions[order_within_valid]
    ordered_p = raw[ordered_positions]
    count = ordered_p.size
    ranks = np.arange(1, count + 1, dtype=float)
    ordered_adjusted = ordered_p * count / ranks
    ordered_adjusted = np.minimum.accumulate(ordered_adjusted[::-1])[::-1]
    adjusted[ordered_positions] = np.minimum(ordered_adjusted, 1.0)

    passes = ordered_p <= alpha * ranks / count
    critical_p_value: float | None = None
    if np.any(passes):
        largest_passing_rank = int(np.flatnonzero(passes)[-1])
        rejected[ordered_positions[: largest_passing_rank + 1]] = True
        critical_p_value = float(ordered_p[largest_passing_rank])
    return BenjaminiHochbergResult(adjusted, rejected, critical_p_value, float(alpha))


def _fit_logistic_newton(
    matrix: np.ndarray,
    targets: np.ndarray,
    *,
    l2_penalty: float,
    max_iterations: int,
    tolerance: float,
) -> LogisticModel:
    row_count, feature_count = matrix.shape
    design = np.column_stack((np.ones(row_count, dtype=float), matrix))
    parameters = np.zeros(feature_count + 1, dtype=float)
    initial_rate = (float(targets.sum()) + 0.5) / (row_count + 1.0)
    parameters[0] = float(np.log(initial_rate) - np.log1p(-initial_rate))

    converged = False
    completed_iterations = 0
    for iteration in range(1, max_iterations + 1):
        linear = design @ parameters
        probability = _stable_sigmoid(linear)
        gradient = design.T @ (probability - targets)
        gradient[1:] += l2_penalty * parameters[1:]
        weights = np.clip(probability * (1.0 - probability), 1e-10, None)
        hessian = design.T @ (design * weights[:, None])
        hessian[1:, 1:] += l2_penalty * np.eye(feature_count)
        hessian.flat[:: hessian.shape[0] + 1] += 1e-12
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(hessian, gradient, rcond=None)[0]

        current_objective = _logistic_objective(
            design,
            targets,
            parameters,
            l2_penalty,
        )
        step_scale = 1.0
        candidate = parameters - step
        while step_scale > 1e-8:
            candidate = parameters - step_scale * step
            candidate_objective = _logistic_objective(
                design,
                targets,
                candidate,
                l2_penalty,
            )
            if np.isfinite(candidate_objective) and candidate_objective <= current_objective:
                break
            step_scale *= 0.5
        if step_scale <= 1e-8:
            completed_iterations = iteration
            break

        parameter_change = float(np.max(np.abs(candidate - parameters)))
        parameters = candidate
        completed_iterations = iteration
        if parameter_change <= tolerance * (1.0 + float(np.max(np.abs(parameters)))):
            converged = True
            break

    if np.any(~np.isfinite(parameters)):
        raise FloatingPointError("logistic optimizer produced non-finite parameters")
    return LogisticModel(
        intercept=float(parameters[0]),
        coefficients=parameters[1:].copy(),
        l2_penalty=float(l2_penalty),
        converged=converged,
        iterations=completed_iterations,
    )


def _logistic_objective(
    design: np.ndarray,
    targets: np.ndarray,
    parameters: np.ndarray,
    l2_penalty: float,
) -> float:
    linear = design @ parameters
    likelihood_loss = np.sum(np.logaddexp(0.0, linear) - targets * linear)
    penalty = 0.5 * l2_penalty * float(parameters[1:] @ parameters[1:])
    return float(likelihood_loss + penalty)


def _paired_metric_delta(
    metric: str,
    labels: np.ndarray,
    challenger: np.ndarray,
    baseline: np.ndarray,
    *,
    threshold: float,
    tail_loss_threshold: float,
    net_returns: np.ndarray | None,
) -> float:
    challenger_value = _bootstrap_metric_value(
        metric,
        labels,
        challenger,
        threshold=threshold,
        tail_loss_threshold=tail_loss_threshold,
        net_returns=net_returns,
    )
    baseline_value = _bootstrap_metric_value(
        metric,
        labels,
        baseline,
        threshold=threshold,
        tail_loss_threshold=tail_loss_threshold,
        net_returns=net_returns,
    )
    return float(challenger_value - baseline_value)


def _bootstrap_metric_value(
    metric: str,
    labels: np.ndarray,
    probability: np.ndarray,
    *,
    threshold: float,
    tail_loss_threshold: float,
    net_returns: np.ndarray | None,
) -> float:
    if metric == "brier":
        return brier_score(labels, probability)
    if metric == "logloss":
        return binary_log_loss(labels, probability)
    metrics = evaluate_probability_predictions(
        labels,
        probability,
        threshold=threshold,
        tail_loss_threshold=tail_loss_threshold,
        net_returns=net_returns,
    )
    return float(metrics[metric])


def _validate_bootstrap_metric(metric: str) -> str:
    allowed = {
        "brier",
        "logloss",
        "precision",
        "recall",
        "f1",
        "balanced_accuracy",
        "lift",
        "mean_net_return",
        "median_net_return",
        "loss_rate",
        "tail_loss_rate",
        "cvar_5",
        "coverage",
    }
    normalized = str(metric).strip().lower()
    if normalized not in allowed:
        raise ValueError("unsupported bootstrap metric: " + normalized)
    if normalized in {
        "mean_net_return",
        "median_net_return",
        "loss_rate",
        "tail_loss_rate",
        "cvar_5",
    }:
        return normalized
    return normalized


def _validate_selection_metric(metric: str) -> str:
    normalized = str(metric).strip().lower()
    if normalized not in {"brier", "logloss"}:
        raise ValueError("selection_metric must be 'brier' or 'logloss'")
    return normalized


def _validate_l2_grid(values: Sequence[float]) -> tuple[float, ...]:
    penalties = tuple(float(value) for value in values)
    if not penalties:
        raise ValueError("l2_grid must not be empty")
    if len(penalties) > 32:
        raise ValueError("l2_grid must contain at most 32 bounded candidates")
    if any(not np.isfinite(value) or value < 0.0 for value in penalties):
        raise ValueError("l2_grid penalties must be finite and nonnegative")
    if len(set(penalties)) != len(penalties):
        raise ValueError("l2_grid penalties must be unique")
    return penalties


def _validate_optimizer_arguments(
    l2_penalty: float,
    max_iterations: int,
    tolerance: float,
) -> None:
    if not np.isfinite(l2_penalty) or l2_penalty < 0.0:
        raise ValueError("l2_penalty must be finite and nonnegative")
    if (
        isinstance(max_iterations, bool)
        or not isinstance(max_iterations, int)
        or max_iterations <= 0
    ):
        raise ValueError("max_iterations must be a positive integer")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")


def _validate_feature_names(
    frame: pd.DataFrame,
    feature_names: Sequence[str],
) -> tuple[str, ...]:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("features must be a pandas DataFrame")
    names = tuple(str(name) for name in feature_names)
    if not names:
        raise ValueError("feature_names must not be empty")
    if len(set(names)) != len(names):
        raise ValueError("feature_names must be unique")
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise ValueError("missing feature columns: " + ", ".join(missing))
    return names


def _numeric_feature_matrix(frame: pd.DataFrame, names: tuple[str, ...]) -> np.ndarray:
    numeric = frame.loc[:, list(names)].apply(pd.to_numeric, errors="coerce")
    return numeric.to_numpy(dtype=float, copy=True)


def _as_finite_matrix(
    values: np.ndarray | pd.DataFrame,
    name: str,
) -> np.ndarray:
    try:
        matrix = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if matrix.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional matrix")
    if matrix.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one row")
    if np.any(~np.isfinite(matrix)):
        raise ValueError(f"{name} must contain only finite values")
    return matrix


def _as_float_vector(values: Sequence[object] | np.ndarray | pd.Series, name: str) -> np.ndarray:
    try:
        vector = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if vector.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    return vector


def _as_binary_vector(
    values: Sequence[object] | np.ndarray | pd.Series,
    name: str,
    *,
    expected_length: int | None = None,
) -> np.ndarray:
    vector = _as_float_vector(values, name)
    if expected_length is not None and vector.size != expected_length:
        raise ValueError(f"{name} length does not match rows")
    if np.any(~np.isfinite(vector)) or np.any((vector != 0.0) & (vector != 1.0)):
        raise ValueError(f"{name} must contain only binary zero/one values")
    return vector


def _as_probability_vector(
    values: Sequence[object] | np.ndarray | pd.Series,
    name: str,
    *,
    expected_length: int | None = None,
) -> np.ndarray:
    vector = _as_float_vector(values, name)
    if expected_length is not None and vector.size != expected_length:
        raise ValueError(f"{name} length does not match rows")
    if np.any(~np.isfinite(vector)) or np.any((vector < 0.0) | (vector > 1.0)):
        raise ValueError(f"{name} must contain finite probabilities between zero and one")
    return vector


def _as_object_vector(
    values: Sequence[object] | np.ndarray | pd.Series,
    name: str,
    *,
    expected_length: int | None = None,
) -> np.ndarray:
    vector = np.asarray(values, dtype=object)
    if vector.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if expected_length is not None and vector.size != expected_length:
        raise ValueError(f"{name} length does not match rows")
    return vector


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0 or not np.isfinite(denominator):
        return float("nan")
    return float(numerator / denominator)


def _stable_sigmoid(values: np.ndarray | float) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    output = np.empty_like(array, dtype=float)
    positive = array >= 0.0
    output[positive] = 1.0 / (1.0 + np.exp(-array[positive]))
    negative_exp = np.exp(array[~positive])
    output[~positive] = negative_exp / (1.0 + negative_exp)
    return output


__all__ = [
    "BenjaminiHochbergResult",
    "BinaryRuleCalibrator",
    "DateBlockBootstrapResult",
    "FeatureTransform",
    "L2SelectionResult",
    "LambdaValidationScore",
    "LogisticModel",
    "PlattCalibrator",
    "ProbabilityChallenger",
    "apply_platt_calibration",
    "benjamini_hochberg",
    "binary_log_loss",
    "brier_score",
    "daily_matched_count_top_k",
    "date_block_bootstrap_paired_delta",
    "evaluate_probability_predictions",
    "expected_calibration_error",
    "fit_binary_rule_calibrator",
    "fit_feature_transform",
    "fit_l2_logistic",
    "fit_platt_calibrator",
    "fit_probability_challenger",
    "predict_binary_rule_proba",
    "predict_logistic_proba",
    "predict_probability_challenger",
    "select_l2_by_validation",
    "transform_features",
]
