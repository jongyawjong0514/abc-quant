"""Model contracts."""

from abc_quant.models.baseline import ConstantBaselineResult, fit_constant_baseline
from abc_quant.models.evaluation import (
    ConstantBaselineEvaluationResult,
    PredictionEvaluationResult,
    evaluate_constant_baseline,
    evaluate_predictions,
)
from abc_quant.models.predictions import (
    SplitPredictionBundle,
    build_constant_baseline_prediction_bundle,
    build_split_prediction_bundle,
)

__all__ = [
    "ConstantBaselineEvaluationResult",
    "ConstantBaselineResult",
    "PredictionEvaluationResult",
    "SplitPredictionBundle",
    "build_constant_baseline_prediction_bundle",
    "build_split_prediction_bundle",
    "evaluate_constant_baseline",
    "evaluate_predictions",
    "fit_constant_baseline",
]
