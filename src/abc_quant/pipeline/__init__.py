"""Pipeline smoke checks."""

from abc_quant.pipeline.contracts import (
    EVALUATION_METRIC_KEYS,
    LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS,
    LINEAR_REGRESSION_SMOKE_SPLITS,
    LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS,
    MODEL_COMPARISON_SMOKE_COMPARISON_KEYS,
    MODEL_COMPARISON_SMOKE_MODEL_KEYS,
    MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS,
    MODEL_COMPARISON_SMOKE_SPLITS,
    MODEL_COMPARISON_SMOKE_SUMMARY_KEYS,
    MODELING_SMOKE_SUMMARY_KEYS,
    PREPROCESSING_SMOKE_SPLITS,
    PREPROCESSING_SMOKE_SUMMARY_KEYS,
    SUPERVISED_DATASET_SMOKE_SPLITS,
    SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS,
    SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS,
    validate_linear_regression_smoke_summary,
    validate_model_comparison_smoke_summary,
    validate_modeling_smoke_summary,
    validate_preprocessing_smoke_summary,
    validate_supervised_dataset_smoke_summary,
)
from abc_quant.pipeline.linear_modeling import run_linear_regression_smoke
from abc_quant.pipeline.lightgbm_diagnostics import run_lightgbm_dependency_smoke
from abc_quant.pipeline.model_comparison import run_model_comparison_smoke
from abc_quant.pipeline.modeling import run_baseline_modeling_smoke
from abc_quant.pipeline.preprocessing import run_preprocessing_smoke
from abc_quant.pipeline.smoke import build_smoke_frame, run_smoke_pipeline
from abc_quant.pipeline.supervised import run_supervised_dataset_smoke

__all__ = [
    "EVALUATION_METRIC_KEYS",
    "LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS",
    "LINEAR_REGRESSION_SMOKE_SPLITS",
    "LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS",
    "MODEL_COMPARISON_SMOKE_COMPARISON_KEYS",
    "MODEL_COMPARISON_SMOKE_MODEL_KEYS",
    "MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS",
    "MODEL_COMPARISON_SMOKE_SPLITS",
    "MODEL_COMPARISON_SMOKE_SUMMARY_KEYS",
    "MODELING_SMOKE_SUMMARY_KEYS",
    "PREPROCESSING_SMOKE_SPLITS",
    "PREPROCESSING_SMOKE_SUMMARY_KEYS",
    "SUPERVISED_DATASET_SMOKE_SPLITS",
    "SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS",
    "SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS",
    "build_smoke_frame",
    "run_baseline_modeling_smoke",
    "run_linear_regression_smoke",
    "run_lightgbm_dependency_smoke",
    "run_model_comparison_smoke",
    "run_preprocessing_smoke",
    "run_supervised_dataset_smoke",
    "run_smoke_pipeline",
    "validate_linear_regression_smoke_summary",
    "validate_model_comparison_smoke_summary",
    "validate_modeling_smoke_summary",
    "validate_preprocessing_smoke_summary",
    "validate_supervised_dataset_smoke_summary",
]
