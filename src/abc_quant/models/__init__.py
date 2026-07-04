"""Model contracts."""

from abc_quant.models.baseline import ConstantBaselineResult, fit_constant_baseline
from abc_quant.models.dataset import (
    SupervisedSplitDataset,
    build_supervised_split_dataset,
)
from abc_quant.models.evaluation import (
    ConstantBaselineEvaluationResult,
    PredictionEvaluationResult,
    SplitPredictionBundleEvaluationResult,
    evaluate_constant_baseline,
    evaluate_prediction_bundle,
    evaluate_predictions,
)
from abc_quant.models.linear import LinearRegressionResult, fit_linear_regression
from abc_quant.models.predictions import (
    SplitPredictionBundle,
    build_constant_baseline_prediction_bundle,
    build_split_prediction_bundle,
)

__all__ = [
    "ConstantBaselineEvaluationResult",
    "ConstantBaselineResult",
    "LinearRegressionResult",
    "PredictionEvaluationResult",
    "SplitPredictionBundle",
    "SplitPredictionBundleEvaluationResult",
    "SupervisedSplitDataset",
    "build_constant_baseline_prediction_bundle",
    "build_split_prediction_bundle",
    "build_supervised_split_dataset",
    "evaluate_constant_baseline",
    "evaluate_prediction_bundle",
    "evaluate_predictions",
    "fit_constant_baseline",
    "fit_linear_regression",
]
