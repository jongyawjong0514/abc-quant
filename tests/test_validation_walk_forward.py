from dataclasses import asdict, replace
import json

import pytest

from abc_quant.validation import (
    WalkForwardSplitPlan,
    WalkForwardWindow,
    build_walk_forward_split_plan,
    validate_walk_forward_split_plan,
)
from abc_quant.validation.walk_forward import WALK_FORWARD_FORBIDDEN_KEYS


def test_build_walk_forward_split_plan_returns_exact_deterministic_windows() -> None:
    plan = build_walk_forward_split_plan(
        12,
        min_train_size=4,
        validation_size=2,
        test_size=2,
    )

    assert isinstance(plan, WalkForwardSplitPlan)
    assert plan.observation_count == 12
    assert plan.min_train_size == 4
    assert plan.validation_size == 2
    assert plan.test_size == 2
    assert plan.step_size == 2
    assert plan.max_windows is None
    assert plan.windows == (
        WalkForwardWindow(
            window_id=0,
            train_start=0,
            train_end=3,
            validation_start=4,
            validation_end=5,
            test_start=6,
            test_end=7,
            train_index=(0, 1, 2, 3),
            validation_index=(4, 5),
            test_index=(6, 7),
        ),
        WalkForwardWindow(
            window_id=1,
            train_start=0,
            train_end=5,
            validation_start=6,
            validation_end=7,
            test_start=8,
            test_end=9,
            train_index=(0, 1, 2, 3, 4, 5),
            validation_index=(6, 7),
            test_index=(8, 9),
        ),
        WalkForwardWindow(
            window_id=2,
            train_start=0,
            train_end=7,
            validation_start=8,
            validation_end=9,
            test_start=10,
            test_end=11,
            train_index=(0, 1, 2, 3, 4, 5, 6, 7),
            validation_index=(8, 9),
            test_index=(10, 11),
        ),
    )
    assert validate_walk_forward_split_plan(plan) is plan
    decoded = json.loads(json.dumps(asdict(plan), sort_keys=True, allow_nan=False))
    assert decoded["observation_count"] == 12
    assert decoded["windows"][0]["train_index"] == [0, 1, 2, 3]


def test_build_walk_forward_split_plan_default_step_size_equals_test_size() -> None:
    default_step = build_walk_forward_split_plan(
        15,
        min_train_size=4,
        validation_size=2,
        test_size=3,
    )
    explicit_step = build_walk_forward_split_plan(
        15,
        min_train_size=4,
        validation_size=2,
        test_size=3,
        step_size=3,
    )

    assert default_step == explicit_step
    assert default_step.step_size == default_step.test_size


def test_build_walk_forward_split_plan_max_windows_truncates_deterministically() -> None:
    plan = build_walk_forward_split_plan(
        20,
        min_train_size=4,
        validation_size=2,
        test_size=2,
        max_windows=2,
    )

    assert plan.max_windows == 2
    assert tuple(window.window_id for window in plan.windows) == (0, 1)
    assert plan.windows[-1].test_index == (8, 9)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"observation_count": 0}, "observation_count must be a positive integer"),
        ({"min_train_size": 0}, "min_train_size must be a positive integer"),
        ({"validation_size": 0}, "validation_size must be a positive integer"),
        ({"test_size": 0}, "test_size must be a positive integer"),
        ({"step_size": 0}, "step_size must be a positive integer"),
        ({"max_windows": 0}, "max_windows must be a positive integer"),
    ],
)
def test_build_walk_forward_split_plan_rejects_invalid_sizes(
    kwargs: dict[str, int],
    message: str,
) -> None:
    params = {
        "observation_count": 12,
        "min_train_size": 4,
        "validation_size": 2,
        "test_size": 2,
        "step_size": 2,
        "max_windows": 2,
    }
    params.update(kwargs)
    observation_count = params.pop("observation_count")

    with pytest.raises(ValueError, match=message):
        build_walk_forward_split_plan(observation_count, **params)


def test_build_walk_forward_split_plan_rejects_no_complete_windows() -> None:
    with pytest.raises(ValueError, match="no complete windows"):
        build_walk_forward_split_plan(
            7,
            min_train_size=4,
            validation_size=2,
            test_size=2,
        )


def test_validate_walk_forward_split_plan_rejects_non_plan() -> None:
    with pytest.raises(TypeError, match="must be a WalkForwardSplitPlan"):
        validate_walk_forward_split_plan(object())


def test_validate_walk_forward_split_plan_rejects_empty_windows() -> None:
    plan = _valid_plan()
    empty = replace(plan, windows=())

    with pytest.raises(ValueError, match="at least one window"):
        validate_walk_forward_split_plan(empty)


def test_validate_walk_forward_split_plan_rejects_duplicate_window_ids() -> None:
    plan = _valid_plan()
    duplicate = replace(
        plan,
        windows=(
            plan.windows[0],
            replace(
                plan.windows[1],
                window_id=0,
                validation_start=6,
                validation_end=7,
                test_start=8,
                test_end=9,
                train_end=5,
                train_index=(0, 1, 2, 3, 4, 5),
            ),
        ),
    )

    with pytest.raises(ValueError, match="ordered"):
        validate_walk_forward_split_plan(duplicate)


def test_validate_walk_forward_split_plan_rejects_non_contiguous_indices() -> None:
    plan = _valid_plan()
    malformed = replace(
        plan,
        windows=(replace(plan.windows[0], train_index=(0, 1, 3)),),
    )

    with pytest.raises(ValueError, match="contiguous positions"):
        validate_walk_forward_split_plan(malformed)


def test_validate_walk_forward_split_plan_rejects_overlapping_indices() -> None:
    plan = _valid_plan()
    malformed = replace(
        plan,
        windows=(replace(plan.windows[0], validation_index=(3, 4)),),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        validate_walk_forward_split_plan(malformed)


def test_validate_walk_forward_split_plan_rejects_out_of_bounds_indices() -> None:
    plan = _valid_plan()
    malformed = replace(
        plan,
        windows=(
            replace(
                plan.windows[0],
                test_end=12,
                test_index=(11, 12),
            ),
        ),
    )

    with pytest.raises(ValueError, match="outside observation_count"):
        validate_walk_forward_split_plan(malformed)


def test_validate_walk_forward_split_plan_rejects_non_json_friendly_values() -> None:
    plan = replace(_valid_plan(), observation_count=float("nan"))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="JSON-friendly"):
        validate_walk_forward_split_plan(plan)


def test_walk_forward_split_plan_does_not_expose_downstream_output_keys() -> None:
    plan = build_walk_forward_split_plan(
        12,
        min_train_size=4,
        validation_size=2,
        test_size=2,
    )

    assert WALK_FORWARD_FORBIDDEN_KEYS.isdisjoint(_all_dict_keys(asdict(plan)))


def _valid_plan() -> WalkForwardSplitPlan:
    return build_walk_forward_split_plan(
        12,
        min_train_size=4,
        validation_size=2,
        test_size=2,
        max_windows=2,
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
