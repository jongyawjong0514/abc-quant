from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from abc_quant.validation.d10_probability_challenger import (
    apply_platt_calibration,
    benjamini_hochberg,
    binary_log_loss,
    daily_matched_count_top_k,
    date_block_bootstrap_paired_delta,
    evaluate_probability_predictions,
    fit_binary_rule_calibrator,
    fit_feature_transform,
    fit_l2_logistic,
    fit_platt_calibrator,
    fit_probability_challenger,
    predict_binary_rule_proba,
    predict_logistic_proba,
    predict_probability_challenger,
    select_l2_by_validation,
    transform_features,
)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def _split_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.DataFrame(
        {
            "momentum": [-2.0, -1.5, -0.7, -0.2, 0.4, 0.9, 1.4, 2.0],
            "volume_slope": [-1.0, -0.8, -0.1, 0.1, 0.3, 0.8, 1.0, 1.4],
            "future_d5_return": np.arange(8, dtype=float),
        }
    )
    validation = pd.DataFrame(
        {
            "momentum": [-1.2, -0.4, 0.5, 1.2],
            "volume_slope": [-0.7, 0.0, 0.5, 1.1],
            "future_d5_return": [100.0, 101.0, 102.0, 103.0],
        }
    )
    calibration = pd.DataFrame(
        {
            "momentum": [-1.0, -0.5, 0.2, 0.8, 1.1, 1.7],
            "volume_slope": [-0.6, -0.2, 0.2, 0.6, 0.9, 1.2],
            "future_d5_return": [200.0, 201.0, 202.0, 203.0, 204.0, 205.0],
        }
    )
    return train, validation, calibration


def test_train_only_transform_handles_constant_nan_and_infinite_features() -> None:
    train = pd.DataFrame(
        {
            "varying": [1.0, np.nan, 3.0, 5.0],
            "constant": [7.0, 7.0, 7.0, 7.0],
            "all_missing": [np.nan, np.nan, np.nan, np.nan],
        }
    )
    transform = fit_feature_transform(train, ["varying", "constant", "all_missing"])

    np.testing.assert_allclose(transform.medians, [3.0, 7.0, 0.0])
    np.testing.assert_allclose(transform.scales[1:], [1.0, 1.0])
    transformed = transform_features(
        pd.DataFrame(
            {
                "varying": [np.nan, np.inf],
                "constant": [7.0, 7.0],
                "all_missing": [np.nan, -np.inf],
                "future_label": [0.0, 999.0],
            }
        ),
        transform,
    )

    assert transformed.shape == (2, 3)
    assert np.isfinite(transformed).all()
    np.testing.assert_allclose(transformed[:, 1:], 0.0)


def test_l2_logistic_newton_is_numerically_stable_and_orders_probabilities() -> None:
    features = np.array([[-1_000.0], [-4.0], [-1.0], [1.0], [4.0], [1_000.0]])
    labels = np.array([0, 0, 0, 1, 1, 1])

    model = fit_l2_logistic(features, labels, l2_penalty=1.0)
    probabilities = predict_logistic_proba(model, features)

    assert np.isfinite(model.intercept)
    assert np.isfinite(model.coefficients).all()
    assert np.isfinite(probabilities).all()
    assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))
    assert np.all(np.diff(probabilities) >= 0.0)
    assert probabilities[0] < 1e-6
    assert probabilities[-1] > 1.0 - 1e-6


def test_validation_grid_selection_and_challenger_predictions_are_bounded() -> None:
    train, validation, calibration = _split_frames()
    train_labels = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    validation_labels = np.array([0, 0, 1, 1])
    calibration_labels = np.array([0, 0, 0, 1, 1, 1])
    feature_names = ["momentum", "volume_slope"]

    selection = select_l2_by_validation(
        train,
        train_labels,
        validation,
        validation_labels,
        feature_names=feature_names,
        l2_grid=(0.01, 0.1, 1.0),
        selection_metric="logloss",
    )
    challenger = fit_probability_challenger(
        train,
        train_labels,
        validation,
        validation_labels,
        calibration,
        calibration_labels,
        feature_names=feature_names,
        l2_grid=(0.01, 0.1, 1.0),
        selection_metric="logloss",
    )
    probability = predict_probability_challenger(challenger, calibration)

    assert len(selection.validation_scores) == 3
    assert selection.model.l2_penalty in {0.01, 0.1, 1.0}
    assert challenger.logistic_model.l2_penalty == selection.model.l2_penalty
    assert np.isfinite(probability).all()
    assert np.all((probability > 0.0) & (probability < 1.0))


def test_platt_calibration_improves_miscalibrated_probabilities() -> None:
    rng = np.random.default_rng(41)
    score = np.linspace(-2.5, 2.5, 2000)
    true_probability = _sigmoid(0.2 + 1.8 * score)
    labels = (rng.random(score.size) < true_probability).astype(float)
    underconfident_probability = _sigmoid(0.02 + 0.25 * score)

    calibrator = fit_platt_calibrator(underconfident_probability, labels)
    calibrated = apply_platt_calibration(calibrator, underconfident_probability)

    assert calibrator.slope > 1.0
    assert binary_log_loss(labels, calibrated) < binary_log_loss(
        labels,
        underconfident_probability,
    )
    assert np.isfinite(calibrated).all()


def test_binary_rule_calibration_returns_two_smoothed_bins() -> None:
    rule = np.array([0, 0, 0, 1, 1, 1, 1])
    labels = np.array([0, 0, 1, 0, 1, 1, 1])

    calibrator = fit_binary_rule_calibrator(rule, labels, smoothing_alpha=1.0)
    probabilities = predict_binary_rule_proba(calibrator, np.array([0, 1, 1, 0]))

    assert calibrator.false_probability == 2.0 / 5.0
    assert calibrator.true_probability == 4.0 / 6.0
    np.testing.assert_allclose(
        probabilities,
        [
            calibrator.false_probability,
            calibrator.true_probability,
            calibrator.true_probability,
            calibrator.false_probability,
        ],
    )


def test_daily_matched_count_top_k_matches_reference_counts_and_breaks_ties_stably() -> None:
    dates = np.array(["2026-01-02"] * 4 + ["2026-01-05"] * 3, dtype=object)
    scores = np.array([0.6, 0.8, 0.8, 0.1, 0.2, 0.9, 0.7])
    reference = np.array([1, 0, 1, 0, 0, 1, 0])

    selected = daily_matched_count_top_k(dates, scores, reference)

    result = pd.DataFrame({"date": dates, "selected": selected})
    reference_frame = pd.DataFrame({"date": dates, "selected": reference})
    assert result.groupby("date")["selected"].sum().to_dict() == (
        reference_frame.groupby("date")["selected"].sum().to_dict()
    )
    assert selected.tolist() == [False, True, True, False, False, True, False]


def test_metrics_include_calibration_returns_coverage_and_empty_dates() -> None:
    labels = np.array([0, 1, 1, 0, 1, 0])
    probabilities = np.array([0.1, 0.8, 0.7, np.nan, 0.55, 0.6])
    returns = np.array([-0.01, 0.12, 0.04, 0.02, -0.08, -0.02])
    dates = np.array(["d1", "d1", "d2", "d2", "d3", "d3"], dtype=object)

    metrics = evaluate_probability_predictions(
        labels,
        probabilities,
        threshold=0.6,
        net_returns=returns,
        dates=dates,
        all_dates=["d1", "d2", "d3", "d4"],
        tail_loss_threshold=-0.05,
    )

    assert metrics["valid_probability_count"] == 5
    assert metrics["selected_count"] == 3
    assert metrics["empty_date_count"] == 1
    assert metrics["selected_date_count"] == 3
    assert metrics["mean_net_return"] == (0.12 + 0.04 - 0.02) / 3.0
    assert metrics["loss_rate"] == 1.0 / 3.0
    assert metrics["tail_loss_rate"] == 0.0
    assert metrics["cvar_5"] == -0.02
    assert metrics["valid_probability_coverage"] == 5.0 / 6.0
    assert 0.0 <= float(metrics["ece"]) <= 1.0


def test_date_block_bootstrap_is_paired_deterministic_and_bh_handles_nan() -> None:
    dates = np.repeat(np.array(["d1", "d2", "d3", "d4"], dtype=object), 3)
    labels = np.tile(np.array([0, 1, 1]), 4)
    challenger = np.tile(np.array([0.1, 0.8, 0.75]), 4)
    baseline = np.tile(np.array([0.4, 0.6, 0.55]), 4)

    first = date_block_bootstrap_paired_delta(
        dates,
        labels,
        challenger,
        baseline,
        metric="brier",
        n_bootstrap=200,
        random_seed=17,
    )
    second = date_block_bootstrap_paired_delta(
        dates,
        labels,
        challenger,
        baseline,
        metric="brier",
        n_bootstrap=200,
        random_seed=17,
    )
    correction = benjamini_hochberg([0.001, 0.02, 0.2, np.nan], alpha=0.05)

    assert first.observed_delta < 0.0
    np.testing.assert_allclose(first.samples, second.samples)
    assert first.effective_bootstrap == 200
    assert first.block_length == 1
    assert first.tail_loss_threshold == -0.05
    assert correction.rejected.tolist() == [True, True, False, False]
    assert np.isnan(correction.adjusted_p_values[-1])
    assert correction.critical_p_value == 0.02


def test_date_block_bootstrap_circular_moving_blocks_are_deterministic() -> None:
    dates = np.repeat(pd.date_range("2026-01-05", periods=12, freq="B"), 2)
    labels = np.tile(np.array([0, 1]), 12)
    challenger = np.tile(np.array([0.2, 0.8]), 12)
    baseline = np.linspace(0.35, 0.65, 24)

    first = date_block_bootstrap_paired_delta(
        dates[::-1],
        labels[::-1],
        challenger[::-1],
        baseline[::-1],
        metric="brier",
        n_bootstrap=100,
        block_length=5,
        random_seed=29,
    )
    second = date_block_bootstrap_paired_delta(
        dates[::-1],
        labels[::-1],
        challenger[::-1],
        baseline[::-1],
        metric="brier",
        n_bootstrap=100,
        block_length=5,
        random_seed=29,
    )

    assert first.block_length == 5
    assert first.effective_bootstrap == 100
    np.testing.assert_allclose(first.samples, second.samples)


@pytest.mark.parametrize("block_length", [0, -1, True, 1.5])
def test_date_block_bootstrap_rejects_invalid_block_length(block_length: object) -> None:
    with pytest.raises(ValueError, match="block_length must be a positive integer"):
        date_block_bootstrap_paired_delta(
            ["2026-01-05", "2026-01-06"],
            [0, 1],
            [0.2, 0.8],
            [0.4, 0.6],
            block_length=block_length,  # type: ignore[arg-type]
        )


def test_mutating_unselected_future_columns_does_not_change_fitted_artifacts() -> None:
    train, validation, calibration = _split_frames()
    train_labels = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    validation_labels = np.array([0, 0, 1, 1])
    calibration_labels = np.array([0, 0, 0, 1, 1, 1])
    feature_names = ["momentum", "volume_slope"]

    baseline = fit_probability_challenger(
        train,
        train_labels,
        validation,
        validation_labels,
        calibration,
        calibration_labels,
        feature_names=feature_names,
        l2_grid=(0.1, 1.0),
    )
    mutated_train = train.copy()
    mutated_validation = validation.copy()
    mutated_calibration = calibration.copy()
    mutated_train["future_d5_return"] = np.arange(8, dtype=float) * -1_000_000.0
    mutated_validation["future_d5_return"] = [9e9, -9e9, 8e9, -8e9]
    mutated_calibration["future_d5_return"] = np.nan
    mutated = fit_probability_challenger(
        mutated_train,
        train_labels,
        mutated_validation,
        validation_labels,
        mutated_calibration,
        calibration_labels,
        feature_names=feature_names,
        l2_grid=(0.1, 1.0),
    )

    np.testing.assert_array_equal(baseline.transform.medians, mutated.transform.medians)
    np.testing.assert_array_equal(baseline.transform.means, mutated.transform.means)
    np.testing.assert_array_equal(baseline.transform.scales, mutated.transform.scales)
    np.testing.assert_array_equal(
        baseline.logistic_model.coefficients,
        mutated.logistic_model.coefficients,
    )
    assert baseline.logistic_model.intercept == mutated.logistic_model.intercept
    assert baseline.platt_calibrator == mutated.platt_calibrator
