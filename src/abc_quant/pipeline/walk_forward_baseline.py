"""Deterministic walk-forward constant-baseline evaluation diagnostics."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Final

import pandas as pd

from abc_quant.data.schema import DATE_COLUMN
from abc_quant.features.matrix import build_feature_matrix
from abc_quant.models.baseline import ConstantBaselineMethod, fit_constant_baseline
from abc_quant.models.dataset import build_supervised_split_dataset
from abc_quant.models.evaluation import evaluate_prediction_bundle
from abc_quant.models.predictions import build_split_prediction_bundle
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)
from abc_quant.preprocessing.scaling import (
    fit_standard_scaler,
    transform_with_standard_scaler,
)
from abc_quant.validation.temporal import TemporalSplit
from abc_quant.validation.walk_forward import (
    WalkForwardWindow,
    build_walk_forward_split_plan,
)

DEFAULT_WALK_FORWARD_BASELINE_MIN_TRAIN_SIZE: Final[int] = 4
DEFAULT_WALK_FORWARD_BASELINE_VALIDATION_SIZE: Final[int] = 2
DEFAULT_WALK_FORWARD_BASELINE_TEST_SIZE: Final[int] = 2
DEFAULT_WALK_FORWARD_BASELINE_STEP_SIZE: Final[int | None] = None
DEFAULT_WALK_FORWARD_BASELINE_MAX_WINDOWS: Final[int | None] = 3
DEFAULT_WALK_FORWARD_BASELINE_METHOD: Final[ConstantBaselineMethod] = "mean"

WALK_FORWARD_BASELINE_SMOKE_SUMMARY_KEYS: Final[tuple[str, ...]] = (
    "observation_count",
    "feature_columns",
    "label_column",
    "baseline_method",
    "plan",
    "windows",
)
WALK_FORWARD_BASELINE_SMOKE_PLAN_KEYS: Final[tuple[str, ...]] = (
    "min_train_size",
    "validation_size",
    "test_size",
    "step_size",
    "max_windows",
    "window_count",
)
WALK_FORWARD_BASELINE_SMOKE_WINDOW_KEYS: Final[tuple[str, ...]] = (
    "window_id",
    "index_ranges",
    "split_counts_before_label_drop",
    "split_counts_after_label_drop",
    "dropped_label_counts",
    "scaler_feature_count",
    "baseline_value",
    "training_label_count",
    "evaluation",
)
WALK_FORWARD_BASELINE_SMOKE_SPLITS: Final[tuple[str, ...]] = (
    "train",
    "validation",
    "test",
)
WALK_FORWARD_BASELINE_SMOKE_INDEX_RANGE_KEYS: Final[tuple[str, ...]] = (
    "start",
    "end",
)
WALK_FORWARD_BASELINE_SMOKE_METRIC_KEYS: Final[tuple[str, ...]] = (
    "split_name",
    "row_count",
    "non_missing_count",
    "missing_actual_count",
    "mae",
    "rmse",
    "mean_error",
    "prediction_mean",
)
WALK_FORWARD_BASELINE_SMOKE_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "raw_features",
        "raw_feature_values",
        "raw_labels",
        "raw_label_values",
        "raw_predictions",
        "raw_prediction_values",
        "winner",
        "rank",
        "ranking",
        "decision",
        "selected_model",
        "selected-model",
        "model_selection",
        "strategy",
        "signal",
        "signals",
        "trading_signals",
        "allocation",
        "allocations",
        "performance_curve",
        "performance-curve",
        "equity_curve",
        "order",
        "orders",
        "position",
        "positions",
        "simulation",
        "simulation_results",
    }
)


def run_walk_forward_baseline_smoke(
    *,
    baseline_method: ConstantBaselineMethod = DEFAULT_WALK_FORWARD_BASELINE_METHOD,
    min_train_size: int = DEFAULT_WALK_FORWARD_BASELINE_MIN_TRAIN_SIZE,
    validation_size: int = DEFAULT_WALK_FORWARD_BASELINE_VALIDATION_SIZE,
    test_size: int = DEFAULT_WALK_FORWARD_BASELINE_TEST_SIZE,
    step_size: int | None = DEFAULT_WALK_FORWARD_BASELINE_STEP_SIZE,
    max_windows: int | None = DEFAULT_WALK_FORWARD_BASELINE_MAX_WINDOWS,
) -> dict[str, Any]:
    """Run deterministic walk-forward constant-baseline diagnostics.

    The helper prepares each walk-forward window independently, fits the
    existing constant baseline from that window's train labels only, and
    returns split-level error diagnostics. It does not choose models or produce
    downstream action artifacts.
    """
    frame = _feature_complete_smoke_frame()
    feature_matrix = build_feature_matrix(
        frame,
        SMOKE_LABEL_COLUMN,
        feature_columns=SMOKE_FEATURE_COLUMNS,
    )
    plan = build_walk_forward_split_plan(
        len(feature_matrix.X),
        min_train_size=min_train_size,
        validation_size=validation_size,
        test_size=test_size,
        step_size=step_size,
        max_windows=max_windows,
    )

    summary = {
        "observation_count": int(plan.observation_count),
        "feature_columns": list(feature_matrix.feature_columns),
        "label_column": feature_matrix.label_column,
        "baseline_method": baseline_method,
        "plan": {
            "min_train_size": int(plan.min_train_size),
            "validation_size": int(plan.validation_size),
            "test_size": int(plan.test_size),
            "step_size": int(plan.step_size),
            "max_windows": None if plan.max_windows is None else int(plan.max_windows),
            "window_count": int(len(plan.windows)),
        },
        "windows": [
            _window_summary(feature_matrix, window, baseline_method=baseline_method)
            for window in plan.windows
        ],
    }
    return validate_walk_forward_baseline_smoke_summary(summary)


def validate_walk_forward_baseline_smoke_summary(summary: object) -> dict[str, Any]:
    """Validate the walk-forward baseline diagnostics summary shape."""
    if not isinstance(summary, dict):
        raise TypeError("walk-forward baseline smoke summary must be a dict")

    forbidden = sorted(
        WALK_FORWARD_BASELINE_SMOKE_FORBIDDEN_KEYS & _collect_nested_keys(summary)
    )
    if forbidden:
        raise ValueError(
            "walk-forward baseline smoke summary contains forbidden keys: "
            + ", ".join(forbidden)
        )

    _validate_key_tuple(
        "walk-forward baseline smoke summary",
        actual_keys=summary.keys(),
        expected_keys=WALK_FORWARD_BASELINE_SMOKE_SUMMARY_KEYS,
    )

    if summary["baseline_method"] not in {"mean", "median"}:
        raise ValueError("walk-forward baseline smoke baseline_method is invalid")
    if not isinstance(summary["feature_columns"], list):
        raise ValueError("walk-forward baseline smoke feature_columns must be a list")
    if not isinstance(summary["windows"], list):
        raise ValueError("walk-forward baseline smoke windows must be a list")
    if not summary["windows"]:
        raise ValueError("walk-forward baseline smoke windows must not be empty")

    plan = summary["plan"]
    if not isinstance(plan, dict):
        raise ValueError("walk-forward baseline smoke plan must be a dict")
    _validate_key_tuple(
        "walk-forward baseline smoke plan",
        actual_keys=plan.keys(),
        expected_keys=WALK_FORWARD_BASELINE_SMOKE_PLAN_KEYS,
    )
    window_count = plan["window_count"]
    if not isinstance(window_count, int) or isinstance(window_count, bool):
        raise ValueError("walk-forward baseline smoke plan window_count must be int")
    if window_count != len(summary["windows"]):
        raise ValueError("walk-forward baseline smoke plan window_count mismatch")

    for window in summary["windows"]:
        _validate_window_summary(window)

    try:
        json.dumps(summary, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("walk-forward baseline smoke summary must be JSON-friendly") from exc

    return summary


def _feature_complete_smoke_frame() -> pd.DataFrame:
    frame = build_smoke_frame()
    return frame.dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(drop=True)


def _window_summary(
    feature_matrix: Any,
    window: WalkForwardWindow,
    *,
    baseline_method: ConstantBaselineMethod,
) -> dict[str, Any]:
    temporal_split = _temporal_split_from_window(feature_matrix.metadata, window)
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
    baseline = fit_constant_baseline(
        feature_matrix,
        temporal_split,
        method=baseline_method,
    )
    prediction_bundle = build_split_prediction_bundle(
        model_name="constant_baseline",
        method=baseline.method,
        train_predictions=_subset_predictions(
            baseline.train_predictions,
            supervised_dataset.train_X.index,
        ),
        validation_predictions=_subset_predictions(
            baseline.validation_predictions,
            supervised_dataset.validation_X.index,
        ),
        test_predictions=_subset_predictions(
            baseline.test_predictions,
            supervised_dataset.test_X.index,
        ),
    )
    evaluation = evaluate_prediction_bundle(feature_matrix, prediction_bundle)

    return {
        "window_id": int(window.window_id),
        "index_ranges": {
            "train": _index_range(window.train_index),
            "validation": _index_range(window.validation_index),
            "test": _index_range(window.test_index),
        },
        "split_counts_before_label_drop": {
            "train": int(len(standardized.train)),
            "validation": int(len(standardized.validation)),
            "test": int(len(standardized.test)),
        },
        "split_counts_after_label_drop": {
            "train": int(len(supervised_dataset.train_X)),
            "validation": int(len(supervised_dataset.validation_X)),
            "test": int(len(supervised_dataset.test_X)),
        },
        "dropped_label_counts": {
            split_name: int(count)
            for split_name, count in supervised_dataset.dropped_label_counts.items()
        },
        "scaler_feature_count": int(len(fitted_scaler.feature_columns)),
        "baseline_value": float(baseline.fitted_value),
        "training_label_count": int(baseline.training_label_count),
        "evaluation": {
            "train": asdict(evaluation.train),
            "validation": asdict(evaluation.validation),
            "test": asdict(evaluation.test),
        },
    }


def _temporal_split_from_window(
    metadata: pd.DataFrame,
    window: WalkForwardWindow,
) -> TemporalSplit:
    dates = pd.to_datetime(metadata[DATE_COLUMN], errors="raise")
    train_dates = dates.iloc[list(window.train_index)]
    validation_dates = dates.iloc[list(window.validation_index)]
    test_dates = dates.iloc[list(window.test_index)]
    return TemporalSplit(
        train_index=window.train_index,
        validation_index=window.validation_index,
        test_index=window.test_index,
        date_column=DATE_COLUMN,
        train_end=train_dates.max(),
        validation_end=validation_dates.max(),
        test_end=test_dates.max(),
        train_start_date=train_dates.min(),
        train_end_date=train_dates.max(),
        validation_start_date=validation_dates.min(),
        validation_end_date=validation_dates.max(),
        test_start_date=test_dates.min(),
        test_end_date=test_dates.max(),
    )


def _subset_predictions(predictions: pd.Series, index: pd.Index) -> pd.Series:
    return predictions.reindex(index).copy(deep=True)


def _index_range(indices: tuple[int, ...]) -> dict[str, int]:
    return {"start": int(indices[0]), "end": int(indices[-1])}


def _validate_window_summary(window: object) -> None:
    if not isinstance(window, dict):
        raise ValueError("walk-forward baseline smoke window summaries must be dicts")
    _validate_key_tuple(
        "walk-forward baseline smoke window",
        actual_keys=window.keys(),
        expected_keys=WALK_FORWARD_BASELINE_SMOKE_WINDOW_KEYS,
    )
    _validate_split_ranges(window["index_ranges"])
    _validate_split_count_mapping(window, "split_counts_before_label_drop")
    _validate_split_count_mapping(window, "split_counts_after_label_drop")
    _validate_split_count_mapping(window, "dropped_label_counts")
    _validate_positive_int(window["scaler_feature_count"], "scaler_feature_count")
    _validate_positive_int(window["training_label_count"], "training_label_count")
    if isinstance(window["baseline_value"], bool) or not isinstance(
        window["baseline_value"],
        int | float,
    ):
        raise ValueError("walk-forward baseline smoke baseline_value must be numeric")
    _validate_evaluation(window["evaluation"])


def _validate_split_ranges(index_ranges: object) -> None:
    if not isinstance(index_ranges, dict):
        raise ValueError("walk-forward baseline smoke index_ranges must be a dict")
    _validate_key_tuple(
        "walk-forward baseline smoke index_ranges",
        actual_keys=index_ranges.keys(),
        expected_keys=WALK_FORWARD_BASELINE_SMOKE_SPLITS,
    )
    for split_name in WALK_FORWARD_BASELINE_SMOKE_SPLITS:
        split_range = index_ranges[split_name]
        if not isinstance(split_range, dict):
            raise ValueError(f"walk-forward index range for {split_name} must be a dict")
        _validate_key_tuple(
            f"walk-forward index range for {split_name}",
            actual_keys=split_range.keys(),
            expected_keys=WALK_FORWARD_BASELINE_SMOKE_INDEX_RANGE_KEYS,
        )
        for key in WALK_FORWARD_BASELINE_SMOKE_INDEX_RANGE_KEYS:
            value = split_range[key]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(
                    f"walk-forward index range for {split_name} {key} "
                    "must be nonnegative int"
                )
        if split_range["end"] < split_range["start"]:
            raise ValueError(f"walk-forward index range for {split_name} is inverted")


def _validate_split_count_mapping(window: dict[str, Any], key: str) -> None:
    split_counts = window[key]
    if not isinstance(split_counts, dict):
        raise ValueError(f"walk-forward baseline smoke {key} must be a dict")
    _validate_key_tuple(
        f"walk-forward baseline smoke {key}",
        actual_keys=split_counts.keys(),
        expected_keys=WALK_FORWARD_BASELINE_SMOKE_SPLITS,
    )
    for split_name in WALK_FORWARD_BASELINE_SMOKE_SPLITS:
        value = split_counts[split_name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(
                f"walk-forward baseline smoke {key} {split_name} "
                "must be nonnegative int"
            )


def _validate_evaluation(evaluation: object) -> None:
    if not isinstance(evaluation, dict):
        raise ValueError("walk-forward baseline smoke evaluation must be a dict")
    _validate_key_tuple(
        "walk-forward baseline smoke evaluation",
        actual_keys=evaluation.keys(),
        expected_keys=WALK_FORWARD_BASELINE_SMOKE_SPLITS,
    )
    for split_name in WALK_FORWARD_BASELINE_SMOKE_SPLITS:
        metrics = evaluation[split_name]
        if not isinstance(metrics, dict):
            raise ValueError(f"walk-forward baseline metrics for {split_name} must be a dict")
        _validate_key_tuple(
            f"walk-forward baseline metrics for {split_name}",
            actual_keys=metrics.keys(),
            expected_keys=WALK_FORWARD_BASELINE_SMOKE_METRIC_KEYS,
        )
        if metrics["split_name"] != split_name:
            raise ValueError(
                f"walk-forward baseline metrics for {split_name} split_name mismatch"
            )


def _validate_positive_int(value: object, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"walk-forward baseline smoke {name} must be positive int")


def _validate_key_tuple(
    context: str,
    *,
    actual_keys: object,
    expected_keys: tuple[str, ...],
) -> None:
    expected = set(expected_keys)
    actual = {str(key) for key in actual_keys}
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{context} keys mismatch: missing={missing}; unknown={unknown}"
        )


def _collect_nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_collect_nested_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_nested_keys(item))
        return keys
    return set()
