"""Model contracts."""

from abc_quant.models.baseline import ConstantBaselineResult, fit_constant_baseline
from abc_quant.models.evaluation import (
    ConstantBaselineEvaluationResult,
    PredictionEvaluationResult,
    evaluate_constant_baseline,
    evaluate_predictions,
)

__all__ = [
    "ConstantBaselineEvaluationResult",
    "ConstantBaselineResult",
    "PredictionEvaluationResult",
    "evaluate_constant_baseline",
    "evaluate_predictions",
    "fit_constant_baseline",
]
