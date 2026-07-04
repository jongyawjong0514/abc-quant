import pandas as pd
import pytest

from abc_quant.models import SplitPredictionBundle, build_split_prediction_bundle


def test_build_split_prediction_bundle_accepts_valid_predictions() -> None:
    bundle = build_split_prediction_bundle(
        model_name=" constant_baseline ",
        method=" median ",
        train_predictions=pd.Series([1.0, 2.0], index=[0, 1], name="prediction"),
        validation_predictions=pd.Series([3.0], index=[2], name="prediction"),
        test_predictions=pd.Series([4.0, 5.0], index=[3, 4], name="prediction"),
    )

    assert isinstance(bundle, SplitPredictionBundle)
    assert bundle.model_name == "constant_baseline"
    assert bundle.method == "median"
    assert bundle.train_predictions.to_dict() == {0: 1.0, 1: 2.0}
    assert bundle.validation_predictions.to_dict() == {2: 3.0}
    assert bundle.test_predictions.to_dict() == {3: 4.0, 4: 5.0}


def test_build_split_prediction_bundle_allows_empty_validation_split() -> None:
    bundle = build_split_prediction_bundle(
        model_name="constant_baseline",
        train_predictions=pd.Series([1.0], index=[0]),
        validation_predictions=pd.Series(dtype="float64"),
        test_predictions=pd.Series([2.0], index=[1]),
    )

    assert bundle.method is None
    assert bundle.validation_predictions.empty


def test_build_split_prediction_bundle_copies_input_series() -> None:
    train = pd.Series([1.0], index=[0])
    validation = pd.Series([2.0], index=[1])
    test = pd.Series([3.0], index=[2])

    bundle = build_split_prediction_bundle(
        model_name="constant_baseline",
        method="mean",
        train_predictions=train,
        validation_predictions=validation,
        test_predictions=test,
    )
    train.iloc[0] = 999.0
    validation.iloc[0] = 888.0
    test.iloc[0] = 777.0

    assert bundle.train_predictions.iloc[0] == 1.0
    assert bundle.validation_predictions.iloc[0] == 2.0
    assert bundle.test_predictions.iloc[0] == 3.0


def test_build_split_prediction_bundle_rejects_empty_model_metadata() -> None:
    predictions = pd.Series([1.0], index=[0])

    with pytest.raises(ValueError, match="model_name must be a non-empty string"):
        build_split_prediction_bundle(
            model_name=" ",
            method="mean",
            train_predictions=predictions,
            validation_predictions=pd.Series(dtype="float64"),
            test_predictions=pd.Series([2.0], index=[1]),
        )

    with pytest.raises(ValueError, match="method must be a non-empty string"):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            method=" ",
            train_predictions=predictions,
            validation_predictions=pd.Series(dtype="float64"),
            test_predictions=pd.Series([2.0], index=[1]),
        )


def test_build_split_prediction_bundle_rejects_non_series_inputs() -> None:
    with pytest.raises(TypeError, match="train_predictions must be a pandas Series"):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            train_predictions=[1.0],  # type: ignore[arg-type]
            validation_predictions=pd.Series(dtype="float64"),
            test_predictions=pd.Series([2.0], index=[1]),
        )


def test_build_split_prediction_bundle_rejects_empty_required_splits() -> None:
    with pytest.raises(ValueError, match="train_predictions must not be empty"):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            train_predictions=pd.Series(dtype="float64"),
            validation_predictions=pd.Series(dtype="float64"),
            test_predictions=pd.Series([2.0], index=[1]),
        )

    with pytest.raises(ValueError, match="test_predictions must not be empty"):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            train_predictions=pd.Series([1.0], index=[0]),
            validation_predictions=pd.Series(dtype="float64"),
            test_predictions=pd.Series(dtype="float64"),
        )


def test_build_split_prediction_bundle_rejects_duplicate_indices() -> None:
    with pytest.raises(ValueError, match="train_predictions index must be unique"):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            train_predictions=pd.Series([1.0, 2.0], index=[0, 0]),
            validation_predictions=pd.Series(dtype="float64"),
            test_predictions=pd.Series([3.0], index=[1]),
        )


def test_build_split_prediction_bundle_rejects_missing_prediction_values() -> None:
    with pytest.raises(
        ValueError,
        match="validation_predictions must not contain missing values",
    ):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            train_predictions=pd.Series([1.0], index=[0]),
            validation_predictions=pd.Series([pd.NA], index=[1]),
            test_predictions=pd.Series([2.0], index=[2]),
        )


def test_build_split_prediction_bundle_rejects_overlapping_indices() -> None:
    with pytest.raises(
        ValueError,
        match="prediction indices must not overlap across splits",
    ):
        build_split_prediction_bundle(
            model_name="constant_baseline",
            train_predictions=pd.Series([1.0], index=[0]),
            validation_predictions=pd.Series([2.0], index=[0]),
            test_predictions=pd.Series([3.0], index=[1]),
        )
