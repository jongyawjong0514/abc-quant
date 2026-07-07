"""Deterministic walk-forward split contracts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Final


WALK_FORWARD_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
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


@dataclass(frozen=True)
class WalkForwardWindow:
    """One contiguous expanding-train walk-forward split window."""

    window_id: int
    train_start: int
    train_end: int
    validation_start: int
    validation_end: int
    test_start: int
    test_end: int
    train_index: tuple[int, ...]
    validation_index: tuple[int, ...]
    test_index: tuple[int, ...]


@dataclass(frozen=True)
class WalkForwardSplitPlan:
    """Deterministic walk-forward split plan over positional observations."""

    observation_count: int
    min_train_size: int
    validation_size: int
    test_size: int
    step_size: int
    max_windows: int | None
    windows: tuple[WalkForwardWindow, ...]


def build_walk_forward_split_plan(
    observation_count: int,
    *,
    min_train_size: int,
    validation_size: int,
    test_size: int,
    step_size: int | None = None,
    max_windows: int | None = None,
) -> WalkForwardSplitPlan:
    """Build a deterministic expanding-train walk-forward split plan.

    The plan operates on integer positions only. It does not inspect data,
    fit models, select models, create strategy outputs, define allocation
    logic, build performance curves, or run simulation engines.
    """
    _validate_positive_integer(observation_count, "observation_count")
    _validate_positive_integer(min_train_size, "min_train_size")
    _validate_positive_integer(validation_size, "validation_size")
    _validate_positive_integer(test_size, "test_size")
    resolved_step_size = test_size if step_size is None else step_size
    _validate_positive_integer(resolved_step_size, "step_size")
    if max_windows is not None:
        _validate_positive_integer(max_windows, "max_windows")

    windows: list[WalkForwardWindow] = []
    offset = 0
    while True:
        train_start = 0
        train_end = min_train_size + offset - 1
        validation_start = train_end + 1
        validation_end = validation_start + validation_size - 1
        test_start = validation_end + 1
        test_end = test_start + test_size - 1
        if test_end >= observation_count:
            break

        windows.append(
            WalkForwardWindow(
                window_id=len(windows),
                train_start=train_start,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
                train_index=tuple(range(train_start, train_end + 1)),
                validation_index=tuple(range(validation_start, validation_end + 1)),
                test_index=tuple(range(test_start, test_end + 1)),
            )
        )
        if max_windows is not None and len(windows) >= max_windows:
            break
        offset += resolved_step_size

    if not windows:
        raise ValueError("walk-forward split plan produced no complete windows")

    return validate_walk_forward_split_plan(
        WalkForwardSplitPlan(
            observation_count=observation_count,
            min_train_size=min_train_size,
            validation_size=validation_size,
            test_size=test_size,
            step_size=resolved_step_size,
            max_windows=max_windows,
            windows=tuple(windows),
        )
    )


def validate_walk_forward_split_plan(plan: object) -> WalkForwardSplitPlan:
    """Validate a walk-forward split plan and return it unchanged when valid."""
    if not isinstance(plan, WalkForwardSplitPlan):
        raise TypeError("walk-forward split plan must be a WalkForwardSplitPlan")

    _validate_json_friendly(plan)
    forbidden = sorted(WALK_FORWARD_FORBIDDEN_KEYS & _collect_nested_keys(asdict(plan)))
    if forbidden:
        raise ValueError(
            "walk-forward split plan contains forbidden keys: " + ", ".join(forbidden)
        )

    _validate_positive_integer(plan.observation_count, "observation_count")
    _validate_positive_integer(plan.min_train_size, "min_train_size")
    _validate_positive_integer(plan.validation_size, "validation_size")
    _validate_positive_integer(plan.test_size, "test_size")
    _validate_positive_integer(plan.step_size, "step_size")
    if plan.max_windows is not None:
        _validate_positive_integer(plan.max_windows, "max_windows")

    if not isinstance(plan.windows, tuple):
        raise ValueError("walk-forward split plan windows must be a tuple")
    if not plan.windows:
        raise ValueError("walk-forward split plan must contain at least one window")
    if plan.max_windows is not None and len(plan.windows) > plan.max_windows:
        raise ValueError("walk-forward split plan has more windows than max_windows")

    window_ids: list[int] = []
    previous_window: WalkForwardWindow | None = None
    for expected_id, window in enumerate(plan.windows):
        if not isinstance(window, WalkForwardWindow):
            raise ValueError("walk-forward split plan windows must be WalkForwardWindow")
        _validate_window(plan, window, expected_id)
        window_ids.append(window.window_id)
        if previous_window is not None:
            _validate_window_progression(plan, previous_window, window)
        previous_window = window

    if len(set(window_ids)) != len(window_ids):
        raise ValueError("walk-forward split plan window_id values must be unique")

    return plan


def _validate_window(
    plan: WalkForwardSplitPlan,
    window: WalkForwardWindow,
    expected_id: int,
) -> None:
    _validate_nonnegative_integer(window.window_id, "window_id")
    if window.window_id != expected_id:
        raise ValueError("walk-forward split plan window_id values must be ordered")
    for field_name in (
        "train_start",
        "train_end",
        "validation_start",
        "validation_end",
        "test_start",
        "test_end",
    ):
        _validate_nonnegative_integer(getattr(window, field_name), field_name)

    if window.train_start != 0:
        raise ValueError("walk-forward train_start must be 0")
    if window.train_end < window.train_start:
        raise ValueError("walk-forward train split must not be empty")
    if window.validation_end < window.validation_start:
        raise ValueError("walk-forward validation split must not be empty")
    if window.test_end < window.test_start:
        raise ValueError("walk-forward test split must not be empty")
    if not (
        window.train_end < window.validation_start
        and window.validation_end < window.test_start
    ):
        raise ValueError("walk-forward split ranges must be ordered train/validation/test")

    _validate_index_tuple(window.train_index, "train_index")
    _validate_index_tuple(window.validation_index, "validation_index")
    _validate_index_tuple(window.test_index, "test_index")
    _validate_no_overlap(window)
    _validate_indices_within_bounds(plan, window)
    _validate_expected_range(
        window.train_index,
        window.train_start,
        window.train_end,
        "train_index",
    )
    _validate_expected_range(
        window.validation_index,
        window.validation_start,
        window.validation_end,
        "validation_index",
    )
    _validate_expected_range(
        window.test_index,
        window.test_start,
        window.test_end,
        "test_index",
    )

    if len(window.train_index) < plan.min_train_size:
        raise ValueError("walk-forward train_index shorter than min_train_size")
    if len(window.validation_index) != plan.validation_size:
        raise ValueError("walk-forward validation_index length must match validation_size")
    if len(window.test_index) != plan.test_size:
        raise ValueError("walk-forward test_index length must match test_size")


def _validate_window_progression(
    plan: WalkForwardSplitPlan,
    previous: WalkForwardWindow,
    current: WalkForwardWindow,
) -> None:
    if current.validation_start != previous.validation_start + plan.step_size:
        raise ValueError("walk-forward validation windows must advance by step_size")
    if current.test_start != previous.test_start + plan.step_size:
        raise ValueError("walk-forward test windows must advance by step_size")
    if current.train_end != previous.train_end + plan.step_size:
        raise ValueError("walk-forward train window must expand by step_size")


def _validate_index_tuple(indices: object, name: str) -> None:
    if not isinstance(indices, tuple):
        raise ValueError(f"{name} must be a tuple")
    if not indices:
        raise ValueError(f"{name} must not be empty")
    for value in indices:
        _validate_nonnegative_integer(value, name)


def _validate_no_overlap(window: WalkForwardWindow) -> None:
    train = set(window.train_index)
    validation = set(window.validation_index)
    test = set(window.test_index)
    if train & validation or train & test or validation & test:
        raise ValueError("walk-forward split indices must not overlap inside a window")


def _validate_indices_within_bounds(
    plan: WalkForwardSplitPlan,
    window: WalkForwardWindow,
) -> None:
    for name, indices in (
        ("train_index", window.train_index),
        ("validation_index", window.validation_index),
        ("test_index", window.test_index),
    ):
        if min(indices) < 0 or max(indices) >= plan.observation_count:
            raise ValueError(f"{name} contains index outside observation_count")


def _validate_expected_range(
    indices: tuple[int, ...],
    start: int,
    end: int,
    name: str,
) -> None:
    expected = tuple(range(start, end + 1))
    if indices != expected:
        raise ValueError(f"{name} must equal contiguous positions {expected}")


def _validate_json_friendly(plan: WalkForwardSplitPlan) -> None:
    try:
        json.dumps(asdict(plan), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("walk-forward split plan must be JSON-friendly") from exc


def _validate_positive_integer(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_nonnegative_integer(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a nonnegative integer")
    if value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


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
