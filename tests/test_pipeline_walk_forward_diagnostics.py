from __future__ import annotations

import builtins
from copy import deepcopy
import json
from typing import Any

import pandas as pd
import pytest

from abc_quant.features.matrix import build_feature_matrix
from abc_quant.pipeline import (
    WALK_FORWARD_SUPERVISED_SMOKE_FORBIDDEN_KEYS,
    WALK_FORWARD_SUPERVISED_SMOKE_INDEX_RANGE_KEYS,
    WALK_FORWARD_SUPERVISED_SMOKE_PLAN_KEYS,
    WALK_FORWARD_SUPERVISED_SMOKE_SPLITS,
    WALK_FORWARD_SUPERVISED_SMOKE_SUMMARY_KEYS,
    WALK_FORWARD_SUPERVISED_SMOKE_WINDOW_KEYS,
    run_walk_forward_supervised_smoke,
    validate_walk_forward_supervised_smoke_summary,
)
import abc_quant.pipeline.walk_forward_diagnostics as walk_forward_diagnostics
from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    build_smoke_frame,
)


def test_walk_forward_supervised_smoke_is_deterministic_and_json_serializable() -> None:
    first = run_walk_forward_supervised_smoke()
    second = run_walk_forward_supervised_smoke()

    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True, allow_nan=False)) == first


def test_walk_forward_supervised_smoke_summary_contract_and_default_windows() -> None:
    summary = run_walk_forward_supervised_smoke()

    assert validate_walk_forward_supervised_smoke_summary(summary) is summary
    assert tuple(summary) == WALK_FORWARD_SUPERVISED_SMOKE_SUMMARY_KEYS
    assert summary["observation_count"] == 18
    assert summary["feature_columns"] == list(SMOKE_FEATURE_COLUMNS)
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert tuple(summary["plan"]) == WALK_FORWARD_SUPERVISED_SMOKE_PLAN_KEYS
    assert summary["plan"] == {
        "min_train_size": 4,
        "validation_size": 2,
        "test_size": 2,
        "step_size": 2,
        "max_windows": None,
        "window_count": 6,
    }
    assert len(summary["windows"]) == 6
    assert [window["window_id"] for window in summary["windows"]] == list(range(6))

    first = summary["windows"][0]
    assert tuple(first) == WALK_FORWARD_SUPERVISED_SMOKE_WINDOW_KEYS
    assert set(first["index_ranges"]) == set(WALK_FORWARD_SUPERVISED_SMOKE_SPLITS)
    assert tuple(first["index_ranges"]["train"]) == (
        WALK_FORWARD_SUPERVISED_SMOKE_INDEX_RANGE_KEYS
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

    last = summary["windows"][-1]
    assert last["index_ranges"] == {
        "train": {"start": 0, "end": 13},
        "validation": {"start": 14, "end": 15},
        "test": {"start": 16, "end": 17},
    }
    assert last["split_counts_after_label_drop"] == {
        "train": 12,
        "validation": 0,
        "test": 0,
    }
    assert last["dropped_label_counts"] == {"train": 2, "validation": 2, "test": 2}


def test_walk_forward_supervised_smoke_supports_window_limit() -> None:
    summary = run_walk_forward_supervised_smoke(max_windows=2)

    assert summary["plan"]["max_windows"] == 2
    assert summary["plan"]["window_count"] == 2
    assert [window["window_id"] for window in summary["windows"]] == [0, 1]


def test_walk_forward_supervised_smoke_scaler_uses_each_window_train_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_fits: list[dict[str, dict[str, float]]] = []
    changed_fits: list[dict[str, dict[str, float]]] = []
    original_fit = walk_forward_diagnostics.fit_standard_scaler

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
        walk_forward_diagnostics,
        "fit_standard_scaler",
        capture_into(baseline_fits),
    )
    run_walk_forward_supervised_smoke(max_windows=1)

    changed_frame = _feature_complete_frame()
    _add_to_feature_matrix_positions(changed_frame, positions=(4, 5, 6, 7), amount=1e9)
    monkeypatch.setattr(
        walk_forward_diagnostics,
        "build_smoke_frame",
        lambda: changed_frame,
    )
    monkeypatch.setattr(
        walk_forward_diagnostics,
        "fit_standard_scaler",
        capture_into(changed_fits),
    )
    run_walk_forward_supervised_smoke(max_windows=1)

    assert len(baseline_fits) == 1
    assert changed_fits == baseline_fits


def test_walk_forward_supervised_smoke_drops_missing_labels_only_from_affected_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed_frame = _feature_complete_frame()
    _set_label_for_feature_matrix_position(changed_frame, position=4, value=float("nan"))
    monkeypatch.setattr(
        walk_forward_diagnostics,
        "build_smoke_frame",
        lambda: changed_frame,
    )

    summary = run_walk_forward_supervised_smoke(max_windows=1)
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


def test_walk_forward_supervised_smoke_validator_rejects_invalid_shapes() -> None:
    summary = run_walk_forward_supervised_smoke(max_windows=1)
    missing_top = deepcopy(summary)
    missing_top.pop("plan")
    with pytest.raises(ValueError, match="missing=\\['plan'\\]"):
        validate_walk_forward_supervised_smoke_summary(missing_top)

    extra_top = deepcopy(summary)
    extra_top["unexpected"] = "value"
    with pytest.raises(ValueError, match="unknown=\\['unexpected'\\]"):
        validate_walk_forward_supervised_smoke_summary(extra_top)

    malformed_window = deepcopy(summary)
    malformed_window["windows"][0].pop("scaler_feature_count")
    with pytest.raises(ValueError, match="missing=\\['scaler_feature_count'\\]"):
        validate_walk_forward_supervised_smoke_summary(malformed_window)

    non_json = deepcopy(summary)
    non_json["observation_count"] = float("nan")
    with pytest.raises(ValueError, match="JSON-friendly"):
        validate_walk_forward_supervised_smoke_summary(non_json)

    forbidden = deepcopy(summary)
    forbidden["windows"][0]["strategy"] = "not allowed"
    with pytest.raises(ValueError, match="forbidden keys: strategy"):
        validate_walk_forward_supervised_smoke_summary(forbidden)


def test_walk_forward_supervised_smoke_validator_rejects_non_dict() -> None:
    with pytest.raises(TypeError, match="must be a dict"):
        validate_walk_forward_supervised_smoke_summary(["not", "a", "dict"])


def test_walk_forward_supervised_smoke_stays_off_lightgbm_runtime_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any):
        if name == "lightgbm" or name.startswith("lightgbm."):
            raise AssertionError("walk-forward supervised smoke must not import LightGBM")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    summary = run_walk_forward_supervised_smoke(max_windows=1)

    assert WALK_FORWARD_SUPERVISED_SMOKE_FORBIDDEN_KEYS.isdisjoint(
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


def _set_label_for_feature_matrix_position(
    frame: pd.DataFrame,
    *,
    position: int,
    value: float,
) -> None:
    metadata = _feature_matrix_metadata(frame, (position,))
    row = metadata.iloc[0]
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
