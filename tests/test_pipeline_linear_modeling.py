from dataclasses import asdict
import json

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models import build_supervised_split_dataset, fit_linear_regression
from abc_quant.models.evaluation import evaluate_prediction_bundle
from abc_quant.pipeline import run_linear_regression_smoke
from abc_quant.pipeline.linear_modeling import (
    DEFAULT_LINEAR_REGRESSION_TRAIN_END,
    DEFAULT_LINEAR_REGRESSION_VALIDATION_END,
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


def test_linear_regression_smoke_is_deterministic_and_json_serializable() -> None:
    first = run_linear_regression_smoke()
    second = run_linear_regression_smoke()

    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_linear_regression_smoke_summary_matches_direct_linear_result() -> None:
    summary = run_linear_regression_smoke()
    _, dataset = _direct_supervised_dataset()
    direct_result = fit_linear_regression(dataset)

    assert summary["model_name"] == direct_result.model_name
    assert summary["method"] == direct_result.method
    assert summary["intercept"] == direct_result.intercept
    assert summary["coefficients"] == {
        column: float(direct_result.coefficients.loc[column])
        for column in direct_result.feature_columns
    }
    assert summary["training_row_count"] == direct_result.training_row_count
    assert summary["prediction_counts"] == {
        "train": len(direct_result.prediction_bundle.train_predictions),
        "validation": len(direct_result.prediction_bundle.validation_predictions),
        "test": len(direct_result.prediction_bundle.test_predictions),
    }


def test_linear_regression_smoke_evaluation_matches_direct_bundle_evaluator() -> None:
    summary = run_linear_regression_smoke()
    feature_matrix, dataset = _direct_supervised_dataset()
    direct_result = fit_linear_regression(dataset)
    direct_evaluation = evaluate_prediction_bundle(
        feature_matrix,
        direct_result.prediction_bundle,
    )

    assert summary["evaluation"] == {
        "train": asdict(direct_evaluation.train),
        "validation": asdict(direct_evaluation.validation),
        "test": asdict(direct_evaluation.test),
    }


def test_linear_regression_smoke_preserves_dataset_contract_metadata() -> None:
    summary = run_linear_regression_smoke()
    _, dataset = _direct_supervised_dataset()

    assert summary["row_count"] == 18
    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert summary["training_row_count"] == len(dataset.train_y)
    assert summary["split_counts_after_label_drop"] == {
        "train": len(dataset.train_X),
        "validation": len(dataset.validation_X),
        "test": len(dataset.test_X),
    }
    assert summary["dropped_label_counts"] == dataset.dropped_label_counts


def test_linear_regression_smoke_does_not_expose_strategy_or_simulation_keys() -> None:
    summary = run_linear_regression_smoke()
    forbidden_keys = {
        "strategy",
        "signal",
        "signals",
        "trading_signals",
        "orders",
        "positions",
        "allocation",
        "allocations",
        "portfolio",
        "portfolio_values",
        "performance_curve",
        "equity_curve",
        "backtest",
        "backtest_results",
        "simulation",
        "simulation_results",
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


def _direct_supervised_dataset():
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
        train_end=DEFAULT_LINEAR_REGRESSION_TRAIN_END,
        validation_end=DEFAULT_LINEAR_REGRESSION_VALIDATION_END,
    )
    fitted_scaler = fit_standard_scaler(feature_matrix, temporal_split)
    standardized = transform_with_standard_scaler(
        feature_matrix,
        fitted_scaler,
        temporal_split,
    )
    return (
        feature_matrix,
        build_supervised_split_dataset(feature_matrix, standardized),
    )


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
