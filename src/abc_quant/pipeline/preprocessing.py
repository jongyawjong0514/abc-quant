"""Deterministic preprocessing smoke diagnostics."""

from __future__ import annotations

from typing import Any, Final

import pandas as pd

from abc_quant.features.matrix import build_feature_matrix
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

DEFAULT_PREPROCESSING_TRAIN_END: Final[str] = "2026-01-07"
DEFAULT_PREPROCESSING_VALIDATION_END: Final[str] = "2026-01-12"


def run_preprocessing_smoke(
    *,
    train_end: str = DEFAULT_PREPROCESSING_TRAIN_END,
    validation_end: str = DEFAULT_PREPROCESSING_VALIDATION_END,
) -> dict[str, Any]:
    """Run deterministic train-only scaling diagnostics.

    The smoke path uses the existing synthetic fixture and in-memory contracts.
    It does not train estimators, tune parameters, change modeling smoke output,
    create allocation logic, build performance curves, or run simulations.
    """
    frame = _feature_complete_smoke_frame()
    feature_matrix = build_feature_matrix(
        frame,
        SMOKE_LABEL_COLUMN,
        feature_columns=SMOKE_FEATURE_COLUMNS,
    )
    temporal_split = build_temporal_split(
        feature_matrix.metadata,
        train_end=train_end,
        validation_end=validation_end,
    )
    fitted_scaler = fit_standard_scaler(feature_matrix, temporal_split)
    standardized = transform_with_standard_scaler(
        feature_matrix,
        fitted_scaler,
        temporal_split,
    )

    return {
        "row_count": int(len(feature_matrix.X)),
        "feature_columns": list(fitted_scaler.feature_columns),
        "split_counts": {
            "train": int(len(temporal_split.train_index)),
            "validation": int(len(temporal_split.validation_index)),
            "test": int(len(temporal_split.test_index)),
        },
        "fitted_means": _series_to_float_dict(
            fitted_scaler.means,
            fitted_scaler.feature_columns,
        ),
        "fitted_stds": _series_to_float_dict(
            fitted_scaler.stds,
            fitted_scaler.feature_columns,
        ),
        "train_mean_after_scaling": _series_to_float_dict(
            standardized.train.mean(axis=0),
            fitted_scaler.feature_columns,
        ),
        "train_std_after_scaling": _series_to_float_dict(
            standardized.train.std(axis=0, ddof=0),
            fitted_scaler.feature_columns,
        ),
        "split_shape": {
            "train": _frame_shape(standardized.train),
            "validation": _frame_shape(standardized.validation),
            "test": _frame_shape(standardized.test),
        },
    }


def _feature_complete_smoke_frame() -> pd.DataFrame:
    frame = build_smoke_frame()
    return frame.dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(drop=True)


def _series_to_float_dict(
    series: pd.Series,
    feature_columns: tuple[str, ...],
) -> dict[str, float]:
    return {column: float(series.loc[column]) for column in feature_columns}


def _frame_shape(frame: pd.DataFrame) -> dict[str, int]:
    return {"rows": int(frame.shape[0]), "columns": int(frame.shape[1])}
