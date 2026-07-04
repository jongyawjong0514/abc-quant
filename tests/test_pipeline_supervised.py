import json

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.dataset import build_supervised_split_dataset
from abc_quant.pipeline import (
    SUPERVISED_DATASET_SMOKE_SPLITS,
    SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS,
    run_supervised_dataset_smoke,
    validate_supervised_dataset_smoke_summary,
)
from abc_quant.pipeline.contracts import SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)
from abc_quant.pipeline.supervised import (
    DEFAULT_SUPERVISED_DATASET_TRAIN_END,
    DEFAULT_SUPERVISED_DATASET_VALIDATION_END,
)
from abc_quant.preprocessing.scaling import (
    fit_standard_scaler,
    transform_with_standard_scaler,
)
from abc_quant.validation.temporal import build_temporal_split


def test_supervised_dataset_smoke_is_deterministic_and_json_serializable() -> None:
    first = run_supervised_dataset_smoke()
    second = run_supervised_dataset_smoke()

    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_supervised_dataset_smoke_summary_contract() -> None:
    summary = run_supervised_dataset_smoke()

    assert validate_supervised_dataset_smoke_summary(summary) is summary
    assert set(summary) == SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS
    assert summary["row_count"] == 18
    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert set(summary["split_counts_before_label_drop"]) == (
        SUPERVISED_DATASET_SMOKE_SPLITS
    )
    assert set(summary["split_counts_after_label_drop"]) == (
        SUPERVISED_DATASET_SMOKE_SPLITS
    )
    assert set(summary["dropped_label_counts"]) == SUPERVISED_DATASET_SMOKE_SPLITS
    assert set(summary["split_shape"]) == SUPERVISED_DATASET_SMOKE_SPLITS
    assert summary["split_counts_before_label_drop"] == {
        "train": 2,
        "validation": 6,
        "test": 10,
    }


def test_supervised_dataset_smoke_matches_direct_dataset_construction() -> None:
    summary = run_supervised_dataset_smoke()
    feature_matrix, standardized = _feature_matrix_and_standardized_features()
    dataset = build_supervised_split_dataset(feature_matrix, standardized)

    assert summary["split_counts_before_label_drop"] == {
        "train": int(len(standardized.train)),
        "validation": int(len(standardized.validation)),
        "test": int(len(standardized.test)),
    }
    assert summary["split_counts_after_label_drop"] == {
        "train": int(len(dataset.train_X)),
        "validation": int(len(dataset.validation_X)),
        "test": int(len(dataset.test_X)),
    }
    assert summary["dropped_label_counts"] == dataset.dropped_label_counts


def test_supervised_dataset_smoke_train_data_remains_non_empty_after_label_drop() -> None:
    summary = run_supervised_dataset_smoke()

    assert summary["split_counts_after_label_drop"]["train"] > 0
    assert summary["split_shape"]["train"]["rows"] == summary[
        "split_counts_after_label_drop"
    ]["train"]
    assert summary["split_shape"]["train"]["columns"] == len(SMOKE_FEATURE_COLUMNS)


def test_supervised_dataset_smoke_preserves_feature_and_label_contract() -> None:
    summary = run_supervised_dataset_smoke()

    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    for split_name in sorted(SUPERVISED_DATASET_SMOKE_SPLITS):
        assert set(summary["split_shape"][split_name]) == (
            SUPERVISED_DATASET_SMOKE_SPLIT_SHAPE_KEYS
        )
        assert summary["split_shape"][split_name]["columns"] == len(
            SMOKE_FEATURE_COLUMNS
        )
        assert summary["split_shape"][split_name]["rows"] == summary[
            "split_counts_after_label_drop"
        ][split_name]


def test_supervised_dataset_smoke_records_label_drop_counts() -> None:
    summary = run_supervised_dataset_smoke()

    assert summary["dropped_label_counts"] == {
        "train": 0,
        "validation": 0,
        "test": 6,
    }
    assert summary["split_counts_after_label_drop"] == {
        "train": 2,
        "validation": 6,
        "test": 4,
    }


def test_supervised_dataset_smoke_does_not_expose_strategy_or_simulation_keys() -> None:
    summary = run_supervised_dataset_smoke()
    forbidden_keys = {
        "strategy",
        "signals",
        "orders",
        "positions",
        "allocations",
        "portfolio",
        "performance_curve",
        "equity_curve",
        "backtest",
        "simulation",
        "simulation_results",
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


def _feature_matrix_and_standardized_features():
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
        train_end=DEFAULT_SUPERVISED_DATASET_TRAIN_END,
        validation_end=DEFAULT_SUPERVISED_DATASET_VALIDATION_END,
    )
    fitted_scaler = fit_standard_scaler(feature_matrix, temporal_split)
    return (
        feature_matrix,
        transform_with_standard_scaler(feature_matrix, fitted_scaler, temporal_split),
    )


def _all_dict_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_all_dict_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_dict_keys(item))
        return keys
    return set()
