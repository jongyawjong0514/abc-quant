import json

import pytest

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.pipeline import (
    PREPROCESSING_SMOKE_SUMMARY_KEYS,
    run_preprocessing_smoke,
    validate_preprocessing_smoke_summary,
)
from abc_quant.pipeline.contracts import PREPROCESSING_SMOKE_SPLITS
from abc_quant.pipeline.preprocessing import (
    DEFAULT_PREPROCESSING_TRAIN_END,
    DEFAULT_PREPROCESSING_VALIDATION_END,
)
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)
from abc_quant.validation.temporal import build_temporal_split


def test_preprocessing_smoke_summary_is_deterministic_and_json_serializable() -> None:
    first = run_preprocessing_smoke()
    second = run_preprocessing_smoke()

    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_preprocessing_smoke_summary_contains_expected_contract() -> None:
    summary = run_preprocessing_smoke()

    assert validate_preprocessing_smoke_summary(summary) is summary
    assert set(summary) == PREPROCESSING_SMOKE_SUMMARY_KEYS
    assert set(summary["split_counts"]) == PREPROCESSING_SMOKE_SPLITS
    assert set(summary["split_shape"]) == PREPROCESSING_SMOKE_SPLITS
    assert summary["row_count"] == 18
    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["split_counts"] == {"train": 2, "validation": 6, "test": 10}
    assert summary["split_shape"] == {
        "train": {"rows": 2, "columns": 4},
        "validation": {"rows": 6, "columns": 4},
        "test": {"rows": 10, "columns": 4},
    }


def test_preprocessing_smoke_fitted_parameters_are_train_only() -> None:
    summary = run_preprocessing_smoke()
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
        train_end=DEFAULT_PREPROCESSING_TRAIN_END,
        validation_end=DEFAULT_PREPROCESSING_VALIDATION_END,
    )
    train_features = feature_matrix.X.iloc[list(temporal_split.train_index)].astype(
        "float64"
    )
    expected_means = train_features.mean(axis=0)
    expected_stds = train_features.std(axis=0, ddof=0)

    for column in SMOKE_FEATURE_COLUMNS:
        assert summary["fitted_means"][column] == pytest.approx(
            float(expected_means.loc[column])
        )
        assert summary["fitted_stds"][column] == pytest.approx(
            float(expected_stds.loc[column])
        )


def test_preprocessing_smoke_train_scaled_mean_and_std_are_standardized() -> None:
    summary = run_preprocessing_smoke()

    for column in SMOKE_FEATURE_COLUMNS:
        assert summary["train_mean_after_scaling"][column] == pytest.approx(0.0)
        assert summary["train_std_after_scaling"][column] == pytest.approx(1.0)


def test_preprocessing_smoke_preserves_validation_and_test_shapes() -> None:
    summary = run_preprocessing_smoke()

    assert summary["split_shape"]["validation"]["rows"] == summary["split_counts"][
        "validation"
    ]
    assert summary["split_shape"]["test"]["rows"] == summary["split_counts"]["test"]
    assert summary["split_shape"]["validation"]["columns"] == len(SMOKE_FEATURE_COLUMNS)
    assert summary["split_shape"]["test"]["columns"] == len(SMOKE_FEATURE_COLUMNS)
