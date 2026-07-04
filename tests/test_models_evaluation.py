from math import sqrt

import pandas as pd
import pytest

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.baseline import fit_constant_baseline
from abc_quant.models.evaluation import (
    ConstantBaselineEvaluationResult,
    PredictionEvaluationResult,
    SplitPredictionBundleEvaluationResult,
    evaluate_constant_baseline,
    evaluate_prediction_bundle,
    evaluate_predictions,
)
from abc_quant.models.predictions import (
    build_constant_baseline_prediction_bundle,
    build_split_prediction_bundle,
)
from abc_quant.validation.temporal import build_temporal_split


LABEL_COLUMN = "label_forward_return_3d_entry_lag_1d"


def test_evaluate_predictions_reports_perfect_prediction_metrics() -> None:
    actual = pd.Series([1.0, 2.0, 3.0], index=[10, 11, 12], name="actual")
    prediction = pd.Series([1.0, 2.0, 3.0], index=[10, 11, 12], name="prediction")

    result = evaluate_predictions(actual, prediction, split_name=" validation ")

    assert isinstance(result, PredictionEvaluationResult)
    assert result.split_name == "validation"
    assert result.row_count == 3
    assert result.non_missing_count == 3
    assert result.missing_actual_count == 0
    assert result.mae == pytest.approx(0.0)
    assert result.rmse == pytest.approx(0.0)
    assert result.mean_error == pytest.approx(0.0)
    assert result.prediction_mean == pytest.approx(2.0)


def test_evaluate_predictions_reports_biased_prediction_metrics() -> None:
    actual = pd.Series([1.0, 2.0, 4.0], index=[0, 1, 2])
    prediction = pd.Series([2.0, 4.0, 4.0], index=[0, 1, 2])

    result = evaluate_predictions(actual, prediction, split_name="test")

    assert result.mae == pytest.approx(1.0)
    assert result.rmse == pytest.approx(sqrt(5.0 / 3.0))
    assert result.mean_error == pytest.approx(1.0)
    assert result.prediction_mean == pytest.approx(10.0 / 3.0)


def test_evaluate_predictions_counts_missing_actuals_without_error_contribution() -> None:
    actual = pd.Series([1.0, pd.NA, 3.0], index=[0, 1, 2], dtype="Float64")
    prediction = pd.Series([1.5, 10.0, 1.0], index=[0, 1, 2])

    result = evaluate_predictions(actual, prediction, split_name="test")

    assert result.row_count == 3
    assert result.non_missing_count == 2
    assert result.missing_actual_count == 1
    assert result.mae == pytest.approx(1.25)
    assert result.rmse == pytest.approx(sqrt(4.25 / 2.0))
    assert result.mean_error == pytest.approx(-0.75)
    assert result.prediction_mean == pytest.approx(12.5 / 3.0)


def test_evaluate_predictions_rejects_invalid_split_index_and_empty_targets() -> None:
    actual = pd.Series([1.0, 2.0], index=[0, 1])

    with pytest.raises(ValueError, match="split_name must not be empty"):
        evaluate_predictions(actual, pd.Series([1.0], index=[0]), split_name=" ")

    with pytest.raises(ValueError, match="must not be empty"):
        evaluate_predictions(actual, pd.Series(dtype="float64"), split_name="train")

    with pytest.raises(ValueError, match="not present in actual labels"):
        evaluate_predictions(actual, pd.Series([1.0], index=[99]), split_name="train")

    with pytest.raises(ValueError, match="no non-missing actual labels"):
        evaluate_predictions(
            pd.Series([pd.NA, pd.NA], index=[0, 1], dtype="Float64"),
            pd.Series([1.0, 2.0], index=[0, 1]),
            split_name="train",
        )


def test_evaluate_constant_baseline_returns_split_evaluations() -> None:
    matrix = build_feature_matrix(_model_frame(), LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-02",
        validation_end="2026-01-03",
    )
    baseline = fit_constant_baseline(matrix, split, method="mean")

    result = evaluate_constant_baseline(matrix, baseline)

    assert isinstance(result, ConstantBaselineEvaluationResult)
    assert result.train.split_name == "train"
    assert result.validation.split_name == "validation"
    assert result.test.split_name == "test"
    assert result.train.row_count == 4
    assert result.train.non_missing_count == 3
    assert result.train.missing_actual_count == 1
    assert result.validation.row_count == 2
    assert result.validation.non_missing_count == 2
    assert result.test.row_count == 4
    assert result.test.non_missing_count == 3
    assert result.test.missing_actual_count == 1
    assert result.train.prediction_mean == pytest.approx(baseline.fitted_value)
    assert result.validation.prediction_mean == pytest.approx(baseline.fitted_value)
    assert result.test.prediction_mean == pytest.approx(baseline.fitted_value)


def test_evaluate_prediction_bundle_returns_split_evaluations() -> None:
    matrix = build_feature_matrix(_model_frame(), LABEL_COLUMN)
    bundle = build_split_prediction_bundle(
        model_name="diagnostic_model",
        method="median",
        train_predictions=pd.Series([1.0, 3.0, 4.0, 7.0], index=[0, 1, 2, 3]),
        validation_predictions=pd.Series([100.0, 200.0], index=[4, 5]),
        test_predictions=pd.Series([300.0, 400.0, 500.0, 600.0], index=[6, 7, 8, 9]),
    )

    result = evaluate_prediction_bundle(matrix, bundle)

    assert isinstance(result, SplitPredictionBundleEvaluationResult)
    assert result.model_name == "diagnostic_model"
    assert result.method == "median"
    assert isinstance(result.train, PredictionEvaluationResult)
    assert isinstance(result.validation, PredictionEvaluationResult)
    assert isinstance(result.test, PredictionEvaluationResult)
    assert result.train.split_name == "train"
    assert result.validation.split_name == "validation"
    assert result.test.split_name == "test"
    assert result.train.row_count == 4
    assert result.validation.row_count == 2
    assert result.test.row_count == 4


def test_evaluate_prediction_bundle_counts_missing_actuals() -> None:
    matrix = build_feature_matrix(_model_frame(), LABEL_COLUMN)
    bundle = build_split_prediction_bundle(
        model_name="diagnostic_model",
        train_predictions=pd.Series([1.0, 3.0, 7.0, 7.0], index=[0, 1, 2, 3]),
        validation_predictions=pd.Series([100.0, 200.0], index=[4, 5]),
        test_predictions=pd.Series([300.0, 400.0, 500.0, 600.0], index=[6, 7, 8, 9]),
    )

    result = evaluate_prediction_bundle(matrix, bundle)

    assert result.train.row_count == 4
    assert result.train.non_missing_count == 3
    assert result.train.missing_actual_count == 1
    assert result.train.mae == pytest.approx(0.0)
    assert result.train.rmse == pytest.approx(0.0)
    assert result.train.mean_error == pytest.approx(0.0)
    assert result.train.prediction_mean == pytest.approx(18.0 / 4.0)
    assert result.test.row_count == 4
    assert result.test.non_missing_count == 3
    assert result.test.missing_actual_count == 1


def test_evaluate_prediction_bundle_rejects_invalid_inputs() -> None:
    matrix = build_feature_matrix(_model_frame(), LABEL_COLUMN)
    bundle = build_split_prediction_bundle(
        model_name="diagnostic_model",
        train_predictions=pd.Series([1.0], index=[0]),
        validation_predictions=pd.Series([2.0], index=[1]),
        test_predictions=pd.Series([3.0], index=[2]),
    )

    with pytest.raises(TypeError, match="feature_matrix must be a FeatureMatrix"):
        evaluate_prediction_bundle(object(), bundle)  # type: ignore[arg-type]

    with pytest.raises(
        TypeError,
        match="prediction_bundle must be a SplitPredictionBundle",
    ):
        evaluate_prediction_bundle(matrix, object())  # type: ignore[arg-type]


def test_evaluate_constant_baseline_bundle_matches_existing_evaluation() -> None:
    matrix = build_feature_matrix(_model_frame(), LABEL_COLUMN)
    split = build_temporal_split(
        matrix.metadata,
        train_end="2026-01-02",
        validation_end="2026-01-03",
    )
    baseline = fit_constant_baseline(matrix, split, method="median")

    direct = evaluate_constant_baseline(matrix, baseline)
    bundled = evaluate_prediction_bundle(
        matrix,
        build_constant_baseline_prediction_bundle(baseline),
    )

    assert bundled.model_name == "constant_baseline"
    assert bundled.method == baseline.method
    assert bundled.train == direct.train
    assert bundled.validation == direct.validation
    assert bundled.test == direct.test


def _model_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labels = {
        ("2026-01-01", "2317"): 1.0,
        ("2026-01-01", "2330"): 3.0,
        ("2026-01-02", "2317"): pd.NA,
        ("2026-01-02", "2330"): 7.0,
        ("2026-01-03", "2317"): 100.0,
        ("2026-01-03", "2330"): 200.0,
        ("2026-01-04", "2317"): 300.0,
        ("2026-01-04", "2330"): 400.0,
        ("2026-01-05", "2317"): pd.NA,
        ("2026-01-05", "2330"): 600.0,
    }
    for ticker in ("2330", "2317"):
        for date in pd.date_range("2026-01-01", periods=5, freq="D"):
            label = labels[(date.strftime("%Y-%m-%d"), ticker)]
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 1000,
                    "feature_alpha": len(rows) + 0.5,
                    LABEL_COLUMN: label,
                }
            )
    return pd.DataFrame(rows)
