from dataclasses import asdict

import pytest

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.baseline import fit_constant_baseline
from abc_quant.models.evaluation import evaluate_prediction_bundle
from abc_quant.models.predictions import build_constant_baseline_prediction_bundle
from abc_quant.pipeline.contracts import (
    EVALUATION_METRIC_KEYS,
    MODELING_SMOKE_SUMMARY_KEYS,
    validate_modeling_smoke_summary,
)
from abc_quant.pipeline.modeling import (
    DEFAULT_TRAIN_END,
    DEFAULT_VALIDATION_END,
    run_baseline_modeling_smoke,
)
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)
from abc_quant.validation.temporal import build_temporal_split


def test_baseline_modeling_smoke_summary_is_deterministic() -> None:
    first = run_baseline_modeling_smoke()
    second = run_baseline_modeling_smoke()

    assert first == second


def test_baseline_modeling_smoke_summary_contains_expected_contract() -> None:
    summary = run_baseline_modeling_smoke()

    assert validate_modeling_smoke_summary(summary) is summary
    assert set(summary) == MODELING_SMOKE_SUMMARY_KEYS
    assert summary["row_count"] == 24
    assert summary["ticker_count"] == 2
    assert summary["rows_per_ticker"] == {"2317": 12, "2330": 12}
    assert summary["split_counts"] == {"train": 8, "validation": 6, "test": 10}
    assert summary["baseline_method"] == "mean"
    assert summary["training_label_count"] == 8
    assert summary["label_non_missing_count"] == 18
    assert summary["label_missing_count"] == 6

    evaluation = summary["evaluation"]
    assert set(evaluation) == {"train", "validation", "test"}
    for split_name, metrics in evaluation.items():
        assert set(metrics) == EVALUATION_METRIC_KEYS
        assert metrics["split_name"] == split_name

    assert evaluation["train"]["row_count"] == 8
    assert evaluation["validation"]["row_count"] == 6
    assert evaluation["test"]["row_count"] == 10
    assert evaluation["test"]["missing_actual_count"] == 6


def test_baseline_modeling_smoke_supports_median_method() -> None:
    mean_summary = run_baseline_modeling_smoke()
    median_summary = run_baseline_modeling_smoke(method="median")
    repeated_median_summary = run_baseline_modeling_smoke(method="median")

    assert median_summary == repeated_median_summary
    assert mean_summary["baseline_method"] == "mean"
    assert median_summary["baseline_method"] == "median"
    assert mean_summary["fitted_value"] == pytest.approx(0.024035964461991133)
    assert median_summary["fitted_value"] == pytest.approx(0.02337506967450309)
    assert median_summary["fitted_value"] != mean_summary["fitted_value"]
    assert median_summary["split_counts"] == mean_summary["split_counts"]
    assert median_summary["training_label_count"] == mean_summary["training_label_count"]


def test_baseline_modeling_smoke_uses_bundle_evaluation_metrics() -> None:
    frame = build_smoke_frame()
    feature_matrix = build_feature_matrix(frame, SMOKE_LABEL_COLUMN)
    temporal_split = build_temporal_split(
        feature_matrix.metadata,
        train_end=DEFAULT_TRAIN_END,
        validation_end=DEFAULT_VALIDATION_END,
    )
    baseline = fit_constant_baseline(feature_matrix, temporal_split)
    direct_evaluation = evaluate_prediction_bundle(
        feature_matrix,
        build_constant_baseline_prediction_bundle(baseline),
    )

    summary = run_baseline_modeling_smoke()

    assert summary["evaluation"] == {
        "train": asdict(direct_evaluation.train),
        "validation": asdict(direct_evaluation.validation),
        "test": asdict(direct_evaluation.test),
    }


def test_baseline_modeling_smoke_keeps_label_out_of_features() -> None:
    summary = run_baseline_modeling_smoke()

    assert summary["feature_columns"] == SMOKE_FEATURE_COLUMNS
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert SMOKE_LABEL_COLUMN not in summary["feature_columns"]


def test_baseline_modeling_smoke_does_not_expose_market_action_or_simulation_keys() -> None:
    summary = run_baseline_modeling_smoke()
    forbidden_keys = {
        "signals",
        "trading_signals",
        "positions",
        "portfolio",
        "portfolio_values",
        "allocations",
        "equity_curve",
        "performance_curve",
        "backtest",
        "backtest_results",
        "simulation",
        "simulation_results",
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


def _all_dict_keys(value: object) -> set[str]:
    if not isinstance(value, dict):
        return set()

    keys = {str(key) for key in value}
    nested_keys: set[str] = set()
    for nested in value.values():
        nested_keys.update(_all_dict_keys(nested))
    return keys | nested_keys
