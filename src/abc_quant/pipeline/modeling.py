"""Deterministic baseline modeling smoke pipeline."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Final

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.baseline import ConstantBaselineMethod, fit_constant_baseline
from abc_quant.models.evaluation import (
    ConstantBaselineEvaluationResult,
    PredictionEvaluationResult,
    evaluate_constant_baseline,
)
from abc_quant.pipeline.contracts import validate_modeling_smoke_summary
from abc_quant.pipeline.smoke import SMOKE_LABEL_COLUMN, build_smoke_frame
from abc_quant.validation.temporal import build_temporal_split

DEFAULT_TRAIN_END: Final[str] = "2026-01-07"
DEFAULT_VALIDATION_END: Final[str] = "2026-01-12"
DEFAULT_BASELINE_METHOD: Final[ConstantBaselineMethod] = "mean"


def run_baseline_modeling_smoke(
    *,
    train_end: str = DEFAULT_TRAIN_END,
    validation_end: str = DEFAULT_VALIDATION_END,
    method: ConstantBaselineMethod = DEFAULT_BASELINE_METHOD,
) -> dict[str, Any]:
    """Run a deterministic model-diagnostics smoke check.

    The pipeline wires existing in-memory contracts together and returns a
    plain diagnostic summary. It does not create market-action outputs,
    allocation outputs, performance curves, or simulation results.
    """
    frame = build_smoke_frame()
    feature_matrix = build_feature_matrix(frame, SMOKE_LABEL_COLUMN)
    temporal_split = build_temporal_split(
        feature_matrix.metadata,
        train_end=train_end,
        validation_end=validation_end,
    )
    baseline = fit_constant_baseline(feature_matrix, temporal_split, method=method)
    evaluation = evaluate_constant_baseline(feature_matrix, baseline)

    summary = {
        "row_count": int(len(frame)),
        "ticker_count": int(frame["ticker"].nunique()),
        "rows_per_ticker": {
            str(ticker): int(count)
            for ticker, count in frame.groupby("ticker", sort=True).size().items()
        },
        "feature_columns": tuple(feature_matrix.feature_columns),
        "label_column": feature_matrix.label_column,
        "label_non_missing_count": int(feature_matrix.y.notna().sum()),
        "label_missing_count": int(feature_matrix.y.isna().sum()),
        "split_counts": {
            "train": len(temporal_split.train_index),
            "validation": len(temporal_split.validation_index),
            "test": len(temporal_split.test_index),
        },
        "fitted_value": float(baseline.fitted_value),
        "baseline_method": baseline.method,
        "training_label_count": int(baseline.training_label_count),
        "evaluation": _evaluation_summary(evaluation),
    }
    return validate_modeling_smoke_summary(summary)


def _evaluation_summary(
    evaluation: ConstantBaselineEvaluationResult,
) -> dict[str, dict[str, object]]:
    return {
        "train": _prediction_evaluation_summary(evaluation.train),
        "validation": _prediction_evaluation_summary(evaluation.validation),
        "test": _prediction_evaluation_summary(evaluation.test),
    }


def _prediction_evaluation_summary(
    result: PredictionEvaluationResult,
) -> dict[str, object]:
    return asdict(result)
