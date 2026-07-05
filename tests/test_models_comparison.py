from dataclasses import FrozenInstanceError

import pytest

from abc_quant.models import (
    PredictionEvaluationComparison,
    PredictionEvaluationResult,
    SplitEvaluationComparison,
    SplitPredictionBundleEvaluationResult,
    compare_prediction_evaluations,
)


def test_compare_prediction_evaluations_returns_candidate_minus_reference_deltas() -> None:
    reference = _evaluation_bundle(
        train=_split("train", mae=2.0, rmse=3.0, mean_error=-1.0, prediction_mean=10.0),
        validation=_split(
            "validation",
            mae=5.0,
            rmse=6.0,
            mean_error=0.5,
            prediction_mean=20.0,
            row_count=4,
            non_missing_count=3,
            missing_actual_count=1,
        ),
        test=_split("test", mae=8.0, rmse=9.0, mean_error=2.0, prediction_mean=30.0),
    )
    candidate = _evaluation_bundle(
        model_name="ordinary_least_squares",
        method="ols_with_intercept",
        train=_split("train", mae=1.5, rmse=4.0, mean_error=-0.25, prediction_mean=12.0),
        validation=_split(
            "validation",
            mae=7.5,
            rmse=5.0,
            mean_error=-1.5,
            prediction_mean=18.0,
            row_count=4,
            non_missing_count=3,
            missing_actual_count=1,
        ),
        test=_split("test", mae=6.0, rmse=11.5, mean_error=3.5, prediction_mean=28.0),
    )

    comparison = compare_prediction_evaluations(
        reference,
        candidate,
        reference_name=" constant_baseline ",
        candidate_name=" ols ",
    )

    assert isinstance(comparison, PredictionEvaluationComparison)
    assert comparison.reference_name == "constant_baseline"
    assert comparison.candidate_name == "ols"
    assert comparison.train == SplitEvaluationComparison(
        split_name="train",
        reference_name="constant_baseline",
        candidate_name="ols",
        row_count=3,
        non_missing_count=3,
        missing_actual_count=0,
        mae_delta=-0.5,
        rmse_delta=1.0,
        mean_error_delta=0.75,
        prediction_mean_delta=2.0,
    )
    assert comparison.validation.split_name == "validation"
    assert comparison.validation.row_count == 4
    assert comparison.validation.non_missing_count == 3
    assert comparison.validation.missing_actual_count == 1
    assert comparison.validation.mae_delta == pytest.approx(2.5)
    assert comparison.validation.rmse_delta == pytest.approx(-1.0)
    assert comparison.validation.mean_error_delta == pytest.approx(-2.0)
    assert comparison.validation.prediction_mean_delta == pytest.approx(-2.0)
    assert comparison.test.split_name == "test"
    assert comparison.test.mae_delta == pytest.approx(-2.0)
    assert comparison.test.rmse_delta == pytest.approx(2.5)
    assert comparison.test.mean_error_delta == pytest.approx(1.5)
    assert comparison.test.prediction_mean_delta == pytest.approx(-2.0)


def test_compare_prediction_evaluations_preserves_negative_deltas_without_decisions() -> None:
    reference = _evaluation_bundle(
        train=_split("train", mae=10.0, rmse=12.0, mean_error=4.0, prediction_mean=5.0),
        validation=_split("validation", mae=10.0, rmse=12.0, mean_error=4.0, prediction_mean=5.0),
        test=_split("test", mae=10.0, rmse=12.0, mean_error=4.0, prediction_mean=5.0),
    )
    candidate = _evaluation_bundle(
        train=_split("train", mae=8.0, rmse=9.0, mean_error=1.0, prediction_mean=2.0),
        validation=_split("validation", mae=8.0, rmse=9.0, mean_error=1.0, prediction_mean=2.0),
        test=_split("test", mae=8.0, rmse=9.0, mean_error=1.0, prediction_mean=2.0),
    )

    comparison = compare_prediction_evaluations(reference, candidate)

    assert comparison.train.mae_delta == pytest.approx(-2.0)
    assert comparison.train.rmse_delta == pytest.approx(-3.0)
    assert comparison.train.mean_error_delta == pytest.approx(-3.0)
    assert comparison.train.prediction_mean_delta == pytest.approx(-3.0)
    assert _all_field_names(comparison).isdisjoint(
        {
            "rank",
            "ranking",
            "winner",
            "decision",
            "selected_model",
            "model_selection",
            "signal",
            "strategy",
        }
    )


def test_compare_prediction_evaluations_rejects_invalid_bundle_types() -> None:
    valid = _evaluation_bundle()

    with pytest.raises(
        TypeError,
        match="reference must be a SplitPredictionBundleEvaluationResult",
    ):
        compare_prediction_evaluations(object(), valid)  # type: ignore[arg-type]

    with pytest.raises(
        TypeError,
        match="candidate must be a SplitPredictionBundleEvaluationResult",
    ):
        compare_prediction_evaluations(valid, object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"reference_name": " "}, "reference_name must be a non-empty string"),
        ({"candidate_name": ""}, "candidate_name must be a non-empty string"),
        ({"reference_name": 1}, "reference_name must be a non-empty string"),
        ({"candidate_name": None}, "candidate_name must be a non-empty string"),
    ],
)
def test_compare_prediction_evaluations_rejects_blank_names(
    kwargs: dict[str, object],
    message: str,
) -> None:
    valid = _evaluation_bundle()

    with pytest.raises(ValueError, match=message):
        compare_prediction_evaluations(valid, valid, **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "candidate_value", "message"),
    [
        ("row_count", 4, "train row_count mismatch: reference=3; candidate=4"),
        (
            "non_missing_count",
            2,
            "train non_missing_count mismatch: reference=3; candidate=2",
        ),
        (
            "missing_actual_count",
            1,
            "train missing_actual_count mismatch: reference=0; candidate=1",
        ),
    ],
)
def test_compare_prediction_evaluations_rejects_mismatched_split_counts(
    field_name: str,
    candidate_value: int,
    message: str,
) -> None:
    reference = _evaluation_bundle()
    candidate_train = _split("train")
    candidate_train = _replace_count(candidate_train, field_name, candidate_value)
    candidate = _evaluation_bundle(train=candidate_train)

    with pytest.raises(ValueError, match=message):
        compare_prediction_evaluations(reference, candidate)


def test_compare_prediction_evaluations_rejects_malformed_split_results() -> None:
    reference = _evaluation_bundle()
    candidate = SplitPredictionBundleEvaluationResult(
        model_name="candidate",
        method=None,
        train=object(),  # type: ignore[arg-type]
        validation=_split("validation"),
        test=_split("test"),
    )

    with pytest.raises(
        TypeError,
        match="train candidate must be a PredictionEvaluationResult",
    ):
        compare_prediction_evaluations(reference, candidate)


def test_prediction_evaluation_comparison_dataclasses_are_frozen() -> None:
    comparison = compare_prediction_evaluations(_evaluation_bundle(), _evaluation_bundle())

    with pytest.raises(FrozenInstanceError):
        comparison.reference_name = "new_reference"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        comparison.train.mae_delta = 1.0  # type: ignore[misc]


def _split(
    split_name: str,
    *,
    row_count: int = 3,
    non_missing_count: int = 3,
    missing_actual_count: int = 0,
    mae: float = 1.0,
    rmse: float = 2.0,
    mean_error: float = 0.5,
    prediction_mean: float = 7.0,
) -> PredictionEvaluationResult:
    return PredictionEvaluationResult(
        split_name=split_name,
        row_count=row_count,
        non_missing_count=non_missing_count,
        missing_actual_count=missing_actual_count,
        mae=mae,
        rmse=rmse,
        mean_error=mean_error,
        prediction_mean=prediction_mean,
    )


def _evaluation_bundle(
    *,
    model_name: str = "constant_baseline",
    method: str | None = "mean",
    train: PredictionEvaluationResult | None = None,
    validation: PredictionEvaluationResult | None = None,
    test: PredictionEvaluationResult | None = None,
) -> SplitPredictionBundleEvaluationResult:
    return SplitPredictionBundleEvaluationResult(
        model_name=model_name,
        method=method,
        train=train or _split("train"),
        validation=validation or _split("validation"),
        test=test or _split("test"),
    )


def _replace_count(
    result: PredictionEvaluationResult,
    field_name: str,
    value: int,
) -> PredictionEvaluationResult:
    values = {
        "split_name": result.split_name,
        "row_count": result.row_count,
        "non_missing_count": result.non_missing_count,
        "missing_actual_count": result.missing_actual_count,
        "mae": result.mae,
        "rmse": result.rmse,
        "mean_error": result.mean_error,
        "prediction_mean": result.prediction_mean,
    }
    values[field_name] = value
    return PredictionEvaluationResult(**values)


def _all_field_names(value: object) -> set[str]:
    if not hasattr(value, "__dataclass_fields__"):
        return set()

    names = set(value.__dataclass_fields__)  # type: ignore[attr-defined]
    nested_names: set[str] = set()
    for name in value.__dataclass_fields__:  # type: ignore[attr-defined]
        nested_names.update(_all_field_names(getattr(value, name)))
    return names | nested_names
