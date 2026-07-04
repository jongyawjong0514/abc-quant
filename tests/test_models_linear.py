from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from abc_quant.models import (
    LinearRegressionResult,
    SplitPredictionBundle,
    SupervisedSplitDataset,
    fit_linear_regression,
)


def _dataset() -> SupervisedSplitDataset:
    feature_columns = ("feature_a", "feature_b")
    train_X = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 2.0, 3.0],
            "feature_b": [1.0, 0.0, 2.0, 1.0],
        },
        index=pd.Index([0, 1, 2, 3], dtype="int64"),
    )
    validation_X = pd.DataFrame(
        {
            "feature_a": [4.0, 5.0],
            "feature_b": [0.0, 2.0],
        },
        index=pd.Index([10, 11], dtype="int64"),
    )
    test_X = pd.DataFrame(
        {
            "feature_a": [6.0, 7.0],
            "feature_b": [1.0, 3.0],
        },
        index=pd.Index([20, 21], dtype="int64"),
    )
    return SupervisedSplitDataset(
        feature_columns=feature_columns,
        label_column="label_forward_return",
        train_X=train_X,
        train_y=_linear_labels(train_X),
        validation_X=validation_X,
        validation_y=pd.Series([100.0, 200.0], index=validation_X.index),
        test_X=test_X,
        test_y=pd.Series([300.0, 400.0], index=test_X.index),
        dropped_label_counts={"train": 0, "validation": 0, "test": 0},
    )


def test_fit_linear_regression_returns_deterministic_coefficients_and_predictions() -> None:
    dataset = _dataset()

    result = fit_linear_regression(dataset)

    assert isinstance(result, LinearRegressionResult)
    assert isinstance(result.prediction_bundle, SplitPredictionBundle)
    assert result.model_name == "ordinary_least_squares"
    assert result.method == "ols_with_intercept"
    assert result.feature_columns == ("feature_a", "feature_b")
    assert result.training_row_count == 4
    assert result.intercept == pytest.approx(1.0)
    assert result.coefficients.to_dict() == pytest.approx(
        {"feature_a": 2.0, "feature_b": -0.5}
    )
    _assert_predictions_match_formula(result.prediction_bundle.train_predictions)
    _assert_predictions_match_formula(result.prediction_bundle.validation_predictions)
    _assert_predictions_match_formula(result.prediction_bundle.test_predictions)


def test_fit_linear_regression_can_omit_intercept() -> None:
    dataset = _dataset()
    no_intercept_train_y = (
        2.0 * dataset.train_X["feature_a"] - 0.5 * dataset.train_X["feature_b"]
    )
    no_intercept_dataset = replace(dataset, train_y=no_intercept_train_y)

    result = fit_linear_regression(no_intercept_dataset, fit_intercept=False)

    assert result.method == "ols_no_intercept"
    assert result.intercept == 0.0
    assert result.coefficients.to_dict() == pytest.approx(
        {"feature_a": 2.0, "feature_b": -0.5}
    )


def test_fit_linear_regression_uses_only_train_labels_for_fit_and_predictions() -> None:
    dataset = _dataset()
    changed_holdout_labels = replace(
        dataset,
        validation_y=pd.Series([-999.0, -888.0], index=dataset.validation_y.index),
        test_y=pd.Series([777.0, 888.0], index=dataset.test_y.index),
    )

    baseline = fit_linear_regression(dataset)
    changed = fit_linear_regression(changed_holdout_labels)

    assert changed.intercept == pytest.approx(baseline.intercept)
    pd.testing.assert_series_equal(changed.coefficients, baseline.coefficients)
    pd.testing.assert_series_equal(
        changed.prediction_bundle.train_predictions,
        baseline.prediction_bundle.train_predictions,
    )
    pd.testing.assert_series_equal(
        changed.prediction_bundle.validation_predictions,
        baseline.prediction_bundle.validation_predictions,
    )
    pd.testing.assert_series_equal(
        changed.prediction_bundle.test_predictions,
        baseline.prediction_bundle.test_predictions,
    )


def test_fit_linear_regression_prediction_indices_match_split_indices() -> None:
    dataset = _dataset()

    result = fit_linear_regression(dataset)

    assert tuple(result.prediction_bundle.train_predictions.index) == tuple(
        dataset.train_X.index
    )
    assert tuple(result.prediction_bundle.validation_predictions.index) == tuple(
        dataset.validation_X.index
    )
    assert tuple(result.prediction_bundle.test_predictions.index) == tuple(
        dataset.test_X.index
    )


def test_fit_linear_regression_rejects_invalid_input_type() -> None:
    with pytest.raises(TypeError, match="dataset must be a SupervisedSplitDataset"):
        fit_linear_regression(object())  # type: ignore[arg-type]


def test_fit_linear_regression_rejects_invalid_train_data() -> None:
    dataset = _dataset()

    with pytest.raises(ValueError, match="non-empty train data"):
        fit_linear_regression(
            replace(
                dataset,
                train_X=dataset.train_X.iloc[0:0],
                train_y=dataset.train_y.iloc[0:0],
            )
        )

    with pytest.raises(ValueError, match="training features contain missing values"):
        fit_linear_regression(
            replace(dataset, train_X=dataset.train_X.assign(feature_a=[0.0, np.nan, 2.0, 3.0]))
        )

    with pytest.raises(ValueError, match="training labels contain missing values"):
        fit_linear_regression(
            replace(
                dataset,
                train_y=pd.Series(
                    [1.0, np.nan, 2.0, 3.0],
                    index=dataset.train_X.index,
                ),
            )
        )

    with pytest.raises(ValueError, match="feature columns must be numeric"):
        fit_linear_regression(
            replace(dataset, train_X=dataset.train_X.assign(feature_a=["x", "y", "z", "w"]))
        )

    with pytest.raises(ValueError, match="training features must be finite"):
        fit_linear_regression(
            replace(dataset, train_X=dataset.train_X.assign(feature_a=[0.0, np.inf, 2.0, 3.0]))
        )

    with pytest.raises(ValueError, match="training labels must be finite"):
        fit_linear_regression(
            replace(
                dataset,
                train_y=pd.Series([1.0, np.inf, 2.0, 3.0], index=dataset.train_X.index),
            )
        )


def test_fit_linear_regression_predictions_are_isolated_from_dataset_mutation() -> None:
    dataset = _dataset()
    result = fit_linear_regression(dataset)
    original_train_prediction = result.prediction_bundle.train_predictions.loc[0]
    original_validation_prediction = result.prediction_bundle.validation_predictions.loc[10]
    original_test_prediction = result.prediction_bundle.test_predictions.loc[20]

    dataset.train_X.loc[0, "feature_a"] = 999.0
    dataset.validation_X.loc[10, "feature_b"] = 888.0
    dataset.test_X.loc[20, "feature_a"] = 777.0

    assert result.prediction_bundle.train_predictions.loc[0] == original_train_prediction
    assert (
        result.prediction_bundle.validation_predictions.loc[10]
        == original_validation_prediction
    )
    assert result.prediction_bundle.test_predictions.loc[20] == original_test_prediction


def _linear_labels(features: pd.DataFrame) -> pd.Series:
    return pd.Series(
        1.0 + 2.0 * features["feature_a"] - 0.5 * features["feature_b"],
        index=features.index,
        name="label_forward_return",
        dtype="float64",
    )


def _assert_predictions_match_formula(predictions: pd.Series) -> None:
    dataset = _dataset()
    features = pd.concat([dataset.train_X, dataset.validation_X, dataset.test_X])
    expected = _linear_labels(features.loc[predictions.index])
    pd.testing.assert_series_equal(
        predictions,
        expected.rename("linear_regression_prediction"),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
