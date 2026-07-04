"""Deterministic supervised dataset smoke diagnostics."""

from __future__ import annotations

from typing import Any, Final

import pandas as pd

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.dataset import build_supervised_split_dataset
from abc_quant.pipeline.preprocessing import (
    DEFAULT_PREPROCESSING_TRAIN_END,
    DEFAULT_PREPROCESSING_VALIDATION_END,
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

DEFAULT_SUPERVISED_DATASET_TRAIN_END: Final[str] = DEFAULT_PREPROCESSING_TRAIN_END
DEFAULT_SUPERVISED_DATASET_VALIDATION_END: Final[str] = (
    DEFAULT_PREPROCESSING_VALIDATION_END
)


def run_supervised_dataset_smoke(
    *,
    train_end: str = DEFAULT_SUPERVISED_DATASET_TRAIN_END,
    validation_end: str = DEFAULT_SUPERVISED_DATASET_VALIDATION_END,
) -> dict[str, Any]:
    """Run deterministic supervised dataset diagnostics.

    The pipeline wires existing in-memory contracts together and returns a
    plain diagnostic summary. It does not train estimators, tune parameters,
    define allocation logic, build performance curves, or run simulations.
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
    supervised_dataset = build_supervised_split_dataset(
        feature_matrix,
        standardized,
        drop_missing_labels=True,
    )

    split_counts_before_label_drop = {
        "train": int(len(standardized.train)),
        "validation": int(len(standardized.validation)),
        "test": int(len(standardized.test)),
    }
    split_counts_after_label_drop = {
        "train": int(len(supervised_dataset.train_X)),
        "validation": int(len(supervised_dataset.validation_X)),
        "test": int(len(supervised_dataset.test_X)),
    }

    return {
        "row_count": int(len(feature_matrix.X)),
        "feature_columns": list(supervised_dataset.feature_columns),
        "label_column": supervised_dataset.label_column,
        "split_counts_before_label_drop": split_counts_before_label_drop,
        "split_counts_after_label_drop": split_counts_after_label_drop,
        "dropped_label_counts": {
            split_name: int(count)
            for split_name, count in supervised_dataset.dropped_label_counts.items()
        },
        "split_shape": {
            "train": _frame_shape(supervised_dataset.train_X),
            "validation": _frame_shape(supervised_dataset.validation_X),
            "test": _frame_shape(supervised_dataset.test_X),
        },
    }


def _feature_complete_smoke_frame() -> pd.DataFrame:
    frame = build_smoke_frame()
    return frame.dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(drop=True)


def _frame_shape(frame: pd.DataFrame) -> dict[str, int]:
    return {"rows": int(frame.shape[0]), "columns": int(frame.shape[1])}
