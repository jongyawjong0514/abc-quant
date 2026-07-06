"""Model contracts."""

from abc_quant.models.baseline import ConstantBaselineResult, fit_constant_baseline
from abc_quant.models.comparison import (
    PredictionEvaluationComparison,
    SplitEvaluationComparison,
    compare_prediction_evaluations,
)
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
from abc_quant.models.lightgbm import (
    LightGBMDependencyStatus,
    LightGBMRegressorParams,
    check_lightgbm_dependency,
    make_default_lightgbm_regressor_params,
    require_lightgbm,
)
from abc_quant.models.predictions import (
    SplitPredictionBundle,
    build_constant_baseline_prediction_bundle,
    build_split_prediction_bundle,
)

__all__ = [
    "ConstantBaselineEvaluationResult",
    "ConstantBaselineResult",
    "LightGBMDependencyStatus",
    "LightGBMRegressorParams",
    "LinearRegressionResult",
    "PredictionEvaluationComparison",
    "PredictionEvaluationResult",
    "SplitPredictionBundle",
    "SplitEvaluationComparison",
    "SplitPredictionBundleEvaluationResult",
    "SupervisedSplitDataset",
    "build_constant_baseline_prediction_bundle",
    "build_split_prediction_bundle",
    "build_supervised_split_dataset",
    "check_lightgbm_dependency",
    "compare_prediction_evaluations",
    "evaluate_constant_baseline",
    "evaluate_prediction_bundle",
    "evaluate_predictions",
    "fit_constant_baseline",
    "fit_linear_regression",
    "make_default_lightgbm_regressor_params",
    "require_lightgbm",
]
