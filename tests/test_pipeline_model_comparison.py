from dataclasses import asdict
import json

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models import (
    build_split_prediction_bundle,
    build_supervised_split_dataset,
    compare_prediction_evaluations,
    fit_constant_baseline,
    fit_linear_regression,
)
from abc_quant.models.evaluation import evaluate_prediction_bundle
from abc_quant.pipeline import run_model_comparison_smoke
from abc_quant.pipeline.model_comparison import (
    DEFAULT_MODEL_COMPARISON_TRAIN_END,
    DEFAULT_MODEL_COMPARISON_VALIDATION_END,
)
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)
from abc_quant.preprocessing.scaling import (
    fit_standard_scaler,
    transform_with_standard_scaler,
)
from abc_quant.validation.temporal import build_temporal_split


SUMMARY_KEYS = {
    "row_count",
    "feature_columns",
    "label_column",
    "reference_model",
    "candidate_model",
    "split_counts",
    "dropped_label_counts",
    "reference_evaluation",
    "candidate_evaluation",
    "comparison",
}
SPLITS = {"train", "validation", "test"}


def test_model_comparison_smoke_is_deterministic_and_json_serializable() -> None:
    first = run_model_comparison_smoke()
    second = run_model_comparison_smoke()

    assert first == second
    assert set(first) == SUMMARY_KEYS
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_model_comparison_smoke_records_model_metadata_and_split_counts() -> None:
    summary = run_model_comparison_smoke()

    assert summary["row_count"] == 18
    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert summary["reference_model"] == {
        "model_name": "constant_baseline",
        "method": "mean",
    }
    assert summary["candidate_model"] == {
        "model_name": "ordinary_least_squares",
        "method": "ols_with_intercept",
    }
    assert summary["split_counts"] == {"train": 2, "validation": 6, "test": 4}
    assert summary["dropped_label_counts"] == {
        "train": 0,
        "validation": 0,
        "test": 6,
    }


def test_model_comparison_smoke_evaluates_same_supervised_prediction_rows() -> None:
    summary = run_model_comparison_smoke()

    assert set(summary["reference_evaluation"]) == {
        "model_name",
        "method",
        "train",
        "validation",
        "test",
    }
    assert set(summary["candidate_evaluation"]) == {
        "model_name",
        "method",
        "train",
        "validation",
        "test",
    }
    assert set(summary["comparison"]) == {
        "reference_name",
        "candidate_name",
        "train",
        "validation",
        "test",
    }

    for split_name in sorted(SPLITS):
        split_count = summary["split_counts"][split_name]
        reference_metrics = summary["reference_evaluation"][split_name]
        candidate_metrics = summary["candidate_evaluation"][split_name]
        comparison_metrics = summary["comparison"][split_name]

        assert reference_metrics["row_count"] == split_count
        assert candidate_metrics["row_count"] == split_count
        assert comparison_metrics["row_count"] == split_count
        assert reference_metrics["non_missing_count"] == split_count
        assert candidate_metrics["non_missing_count"] == split_count
        assert comparison_metrics["non_missing_count"] == split_count
        assert reference_metrics["missing_actual_count"] == 0
        assert candidate_metrics["missing_actual_count"] == 0
        assert comparison_metrics["missing_actual_count"] == 0


def test_model_comparison_smoke_matches_direct_comparison_contract() -> None:
    summary = run_model_comparison_smoke()
    reference_evaluation, candidate_evaluation, comparison = _direct_evaluations()

    assert summary["reference_evaluation"] == asdict(reference_evaluation)
    assert summary["candidate_evaluation"] == asdict(candidate_evaluation)
    assert summary["comparison"] == asdict(comparison)


def test_model_comparison_smoke_does_not_expose_decision_or_simulation_keys() -> None:
    summary = run_model_comparison_smoke()
    forbidden_keys = {
        "winner",
        "rank",
        "ranking",
        "decision",
        "selected_model",
        "model_selection",
        "strategy",
        "signal",
        "signals",
        "trading_signals",
        "allocation",
        "allocations",
        "performance_curve",
        "equity_curve",
        "order",
        "orders",
        "position",
        "positions",
        "simulation",
        "simulation_results",
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


def _direct_evaluations():
    frame = build_smoke_frame().dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(
        drop=True
    )
    feature_matrix = build_feature_matrix(
        frame,
        SMOKE_LABEL_COLUMN,
        feature_columns=SMOKE_FEATURE_COLUMNS,
    )
    temporal_split = build_temporal_split(
        feature_matrix.metadata,
        train_end=DEFAULT_MODEL_COMPARISON_TRAIN_END,
        validation_end=DEFAULT_MODEL_COMPARISON_VALIDATION_END,
    )
    fitted_scaler = fit_standard_scaler(feature_matrix, temporal_split)
    standardized = transform_with_standard_scaler(
        feature_matrix,
        fitted_scaler,
        temporal_split,
    )
    dataset = build_supervised_split_dataset(feature_matrix, standardized)
    baseline = fit_constant_baseline(feature_matrix, temporal_split)
    reference_bundle = build_split_prediction_bundle(
        model_name="constant_baseline",
        method=baseline.method,
        train_predictions=baseline.train_predictions.reindex(dataset.train_X.index),
        validation_predictions=baseline.validation_predictions.reindex(
            dataset.validation_X.index
        ),
        test_predictions=baseline.test_predictions.reindex(dataset.test_X.index),
    )
    linear_result = fit_linear_regression(dataset)
    reference_evaluation = evaluate_prediction_bundle(feature_matrix, reference_bundle)
    candidate_evaluation = evaluate_prediction_bundle(
        feature_matrix,
        linear_result.prediction_bundle,
    )
    comparison = compare_prediction_evaluations(
        reference_evaluation,
        candidate_evaluation,
        reference_name=reference_evaluation.model_name,
        candidate_name=candidate_evaluation.model_name,
    )
    return reference_evaluation, candidate_evaluation, comparison


def _all_dict_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_all_dict_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_dict_keys(item))
        return keys
    return set()
