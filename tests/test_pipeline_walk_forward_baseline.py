from __future__ import annotations

import builtins
from copy import deepcopy
import json
from typing import Any

import pandas as pd
import pytest

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.pipeline import (
    WALK_FORWARD_BASELINE_SMOKE_FORBIDDEN_KEYS,
    WALK_FORWARD_BASELINE_SMOKE_INDEX_RANGE_KEYS,
    WALK_FORWARD_BASELINE_SMOKE_METRIC_KEYS,
    WALK_FORWARD_BASELINE_SMOKE_PLAN_KEYS,
    WALK_FORWARD_BASELINE_SMOKE_SPLITS,
    WALK_FORWARD_BASELINE_SMOKE_SUMMARY_KEYS,
    WALK_FORWARD_BASELINE_SMOKE_WINDOW_KEYS,
    run_walk_forward_baseline_smoke,
    validate_walk_forward_baseline_smoke_summary,
)
import abc_quant.pipeline.walk_forward_baseline as walk_forward_baseline
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)


def test_walk_forward_baseline_smoke_is_deterministic_and_json_serializable() -> None:
    first = run_walk_forward_baseline_smoke()
    second = run_walk_forward_baseline_smoke()

    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True, allow_nan=False)) == first


def test_walk_forward_baseline_smoke_summary_contract_and_default_windows() -> None:
    summary = run_walk_forward_baseline_smoke()

    assert validate_walk_forward_baseline_smoke_summary(summary) is summary
    assert tuple(summary) == WALK_FORWARD_BASELINE_SMOKE_SUMMARY_KEYS
    assert summary["observation_count"] == 18
    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert summary["baseline_method"] == "mean"
    assert tuple(summary["plan"]) == WALK_FORWARD_BASELINE_SMOKE_PLAN_KEYS
    assert summary["plan"] == {
        "min_train_size": 4,
        "validation_size": 2,
        "test_size": 2,
        "step_size": 2,
        "max_windows": 3,
        "window_count": 3,
    }
    assert [window["window_id"] for window in summary["windows"]] == [0, 1, 2]

    first = summary["windows"][0]
    assert tuple(first) == WALK_FORWARD_BASELINE_SMOKE_WINDOW_KEYS
    assert set(first["index_ranges"]) == set(WALK_FORWARD_BASELINE_SMOKE_SPLITS)
    assert tuple(first["index_ranges"]["train"]) == (
        WALK_FORWARD_BASELINE_SMOKE_INDEX_RANGE_KEYS
    )
    assert first["index_ranges"] == {
        "train": {"start": 0, "end": 3},
        "validation": {"start": 4, "end": 5},
        "test": {"start": 6, "end": 7},
    }
    assert first["split_counts_before_label_drop"] == {
        "train": 4,
        "validation": 2,
        "test": 2,
    }
    assert first["split_counts_after_label_drop"] == {
        "train": 4,
        "validation": 2,
        "test": 2,
    }
    assert first["dropped_label_counts"] == {"train": 0, "validation": 0, "test": 0}
    assert first["scaler_feature_count"] == len(SMOKE_FEATURE_COLUMNS)
    assert first["training_label_count"] == 4
    assert first["baseline_value"] == pytest.approx(0.024210705719453496)
    assert set(first["evaluation"]) == set(WALK_FORWARD_BASELINE_SMOKE_SPLITS)
    for split_name in WALK_FORWARD_BASELINE_SMOKE_SPLITS:
        metrics = first["evaluation"][split_name]
        assert tuple(metrics) == WALK_FORWARD_BASELINE_SMOKE_METRIC_KEYS
        assert metrics["split_name"] == split_name
        assert metrics["row_count"] == first["split_counts_after_label_drop"][split_name]
        assert metrics["non_missing_count"] == metrics["row_count"]
        assert metrics["missing_actual_count"] == 0


def test_walk_forward_baseline_smoke_supports_existing_median_baseline_method() -> None:
    summary = run_walk_forward_baseline_smoke(baseline_method="median", max_windows=1)

    assert summary["baseline_method"] == "median"
    assert summary["windows"][0]["baseline_value"] == pytest.approx(0.023717805534439806)


def test_walk_forward_baseline_smoke_uses_train_labels_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = run_walk_forward_baseline_smoke(max_windows=1)
    changed_frame = _feature_complete_frame()
    _set_label_for_feature_matrix_positions(
        changed_frame,
        positions=(4, 5, 6, 7),
        values=(-999.0, -999.0, 999.0, 999.0),
    )
    monkeypatch.setattr(
        walk_forward_baseline,
        "build_smoke_frame",
        lambda: changed_frame,
    )
    changed = run_walk_forward_baseline_smoke(max_windows=1)

    assert changed["windows"][0]["baseline_value"] == baseline["windows"][0][
        "baseline_value"
    ]
    assert changed["windows"][0]["evaluation"] != baseline["windows"][0]["evaluation"]


def test_walk_forward_baseline_smoke_scaler_uses_each_window_train_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_fits: list[dict[str, dict[str, float]]] = []
    changed_fits: list[dict[str, dict[str, float]]] = []
    original_fit = walk_forward_baseline.fit_standard_scaler

    def capture_into(storage: list[dict[str, dict[str, float]]]):
        def spy_fit(*args: Any, **kwargs: Any):
            fitted = original_fit(*args, **kwargs)
            storage.append(
                {
                    "means": {
                        column: float(fitted.means.loc[column])
                        for column in fitted.feature_columns
                    },
                    "stds": {
                        column: float(fitted.stds.loc[column])
                        for column in fitted.feature_columns
                    },
                }
            )
            return fitted

        return spy_fit

    monkeypatch.setattr(
        walk_forward_baseline,
        "fit_standard_scaler",
        capture_into(baseline_fits),
    )
    run_walk_forward_baseline_smoke(max_windows=1)

    changed_frame = _feature_complete_frame()
    _add_to_feature_matrix_positions(changed_frame, positions=(4, 5, 6, 7), amount=1e9)
    monkeypatch.setattr(
        walk_forward_baseline,
        "build_smoke_frame",
        lambda: changed_frame,
    )
    monkeypatch.setattr(
        walk_forward_baseline,
        "fit_standard_scaler",
        capture_into(changed_fits),
    )
    run_walk_forward_baseline_smoke(max_windows=1)

    assert len(baseline_fits) == 1
    assert changed_fits == baseline_fits


def test_walk_forward_baseline_smoke_drops_missing_labels_only_from_affected_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed_frame = _feature_complete_frame()
    _set_label_for_feature_matrix_positions(
        changed_frame,
        positions=(4,),
        values=(float("nan"),),
    )
    monkeypatch.setattr(
        walk_forward_baseline,
        "build_smoke_frame",
        lambda: changed_frame,
    )

    summary = run_walk_forward_baseline_smoke(max_windows=1)
    window = summary["windows"][0]

    assert window["split_counts_before_label_drop"] == {
        "train": 4,
        "validation": 2,
        "test": 2,
    }
    assert window["split_counts_after_label_drop"] == {
        "train": 4,
        "validation": 1,
        "test": 2,
    }
    assert window["dropped_label_counts"] == {
        "train": 0,
        "validation": 1,
        "test": 0,
    }
    assert window["evaluation"]["validation"]["row_count"] == 1
    assert window["evaluation"]["train"]["row_count"] == 4
    assert window["evaluation"]["test"]["row_count"] == 2


def test_walk_forward_baseline_smoke_validator_rejects_invalid_shapes() -> None:
    summary = run_walk_forward_baseline_smoke(max_windows=1)
    missing_top = deepcopy(summary)
    missing_top.pop("baseline_method")
    with pytest.raises(ValueError, match="missing=\\['baseline_method'\\]"):
        validate_walk_forward_baseline_smoke_summary(missing_top)

    extra_top = deepcopy(summary)
    extra_top["unexpected"] = "value"
    with pytest.raises(ValueError, match="unknown=\\['unexpected'\\]"):
        validate_walk_forward_baseline_smoke_summary(extra_top)

    malformed_window = deepcopy(summary)
    malformed_window["windows"][0].pop("baseline_value")
    with pytest.raises(ValueError, match="missing=\\['baseline_value'\\]"):
        validate_walk_forward_baseline_smoke_summary(malformed_window)

    malformed_metric = deepcopy(summary)
    malformed_metric["windows"][0]["evaluation"]["train"].pop("mae")
    with pytest.raises(ValueError, match="missing=\\['mae'\\]"):
        validate_walk_forward_baseline_smoke_summary(malformed_metric)

    non_json = deepcopy(summary)
    non_json["windows"][0]["baseline_value"] = float("nan")
    with pytest.raises(ValueError, match="JSON-friendly"):
        validate_walk_forward_baseline_smoke_summary(non_json)

    forbidden = deepcopy(summary)
    forbidden["windows"][0]["strategy"] = "not allowed"
    with pytest.raises(ValueError, match="forbidden keys: strategy"):
        validate_walk_forward_baseline_smoke_summary(forbidden)


def test_walk_forward_baseline_smoke_validator_rejects_non_dict() -> None:
    with pytest.raises(TypeError, match="must be a dict"):
        validate_walk_forward_baseline_smoke_summary(["not", "a", "dict"])


def test_walk_forward_baseline_smoke_stays_off_lightgbm_runtime_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any):
        if name == "lightgbm" or name.startswith("lightgbm."):
            raise AssertionError("walk-forward baseline smoke must not import LightGBM")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    summary = run_walk_forward_baseline_smoke(max_windows=1)

    assert WALK_FORWARD_BASELINE_SMOKE_FORBIDDEN_KEYS.isdisjoint(
        _all_dict_keys(summary)
    )


def _feature_complete_frame() -> pd.DataFrame:
    return build_smoke_frame().dropna(subset=list(SMOKE_FEATURE_COLUMNS)).reset_index(
        drop=True
    )


def _add_to_feature_matrix_positions(
    frame: pd.DataFrame,
    *,
    positions: tuple[int, ...],
    amount: float,
) -> None:
    metadata = _feature_matrix_metadata(frame, positions)
    for _, row in metadata.iterrows():
        mask = (frame["date"] == row["date"]) & (frame["ticker"] == row["ticker"])
        frame.loc[mask, list(SMOKE_FEATURE_COLUMNS)] = (
            frame.loc[mask, list(SMOKE_FEATURE_COLUMNS)] + amount
        )


def _set_label_for_feature_matrix_positions(
    frame: pd.DataFrame,
    *,
    positions: tuple[int, ...],
    values: tuple[float, ...],
) -> None:
    metadata = _feature_matrix_metadata(frame, positions)
    for (_, row), value in zip(metadata.iterrows(), values, strict=True):
        mask = (frame["date"] == row["date"]) & (frame["ticker"] == row["ticker"])
        frame.loc[mask, SMOKE_LABEL_COLUMN] = value


def _feature_matrix_metadata(
    frame: pd.DataFrame,
    positions: tuple[int, ...],
) -> pd.DataFrame:
    feature_matrix = build_feature_matrix(
        frame,
        SMOKE_LABEL_COLUMN,
        feature_columns=SMOKE_FEATURE_COLUMNS,
    )
    return feature_matrix.metadata.iloc[list(positions)].copy()


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
