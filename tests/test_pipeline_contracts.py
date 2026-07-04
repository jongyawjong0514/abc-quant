from __future__ import annotations

from copy import deepcopy

import pytest

from abc_quant.pipeline.contracts import (
    EVALUATION_METRIC_KEYS,
    MODELING_SMOKE_SUMMARY_KEYS,
    PREPROCESSING_SMOKE_SPLITS,
    PREPROCESSING_SMOKE_SUMMARY_KEYS,
    validate_modeling_smoke_summary,
    validate_preprocessing_smoke_summary,
)
from abc_quant.pipeline.modeling import run_baseline_modeling_smoke
from abc_quant.pipeline.preprocessing import run_preprocessing_smoke


def test_validate_modeling_smoke_summary_accepts_valid_summary() -> None:
    summary = run_baseline_modeling_smoke()

    assert validate_modeling_smoke_summary(summary) is summary
    assert set(summary) == MODELING_SMOKE_SUMMARY_KEYS
    assert set(summary["evaluation"]["train"]) == EVALUATION_METRIC_KEYS


def test_validate_modeling_smoke_summary_rejects_non_dict() -> None:
    with pytest.raises(ValueError, match="modeling smoke summary must be a dict"):
        validate_modeling_smoke_summary(["not", "a", "dict"])


def test_validate_modeling_smoke_summary_rejects_invalid_baseline_method() -> None:
    summary = run_baseline_modeling_smoke()
    summary["baseline_method"] = "mode"

    with pytest.raises(
        ValueError,
        match="modeling smoke summary baseline_method must be one of: mean, median",
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_missing_top_level_key() -> None:
    summary = run_baseline_modeling_smoke()
    del summary["row_count"]

    with pytest.raises(
        ValueError,
        match=r"modeling smoke summary keys mismatch: .*missing=\['row_count'\]",
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_unknown_top_level_key() -> None:
    summary = run_baseline_modeling_smoke()
    summary["unexpected"] = True

    with pytest.raises(
        ValueError,
        match=r"modeling smoke summary keys mismatch: .*unknown=\['unexpected'\]",
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_non_dict_evaluation() -> None:
    summary = run_baseline_modeling_smoke()
    summary["evaluation"] = []

    with pytest.raises(
        ValueError,
        match="modeling smoke summary evaluation must be a dict",
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_missing_evaluation_split() -> None:
    summary = run_baseline_modeling_smoke()
    del summary["evaluation"]["test"]

    with pytest.raises(
        ValueError,
        match=(
            r"modeling smoke summary evaluation keys mismatch: "
            r".*missing=\['test'\]"
        ),
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_unknown_evaluation_split() -> None:
    summary = run_baseline_modeling_smoke()
    summary["evaluation"]["holdout"] = deepcopy(summary["evaluation"]["test"])

    with pytest.raises(
        ValueError,
        match=(
            r"modeling smoke summary evaluation keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_non_dict_metrics() -> None:
    summary = run_baseline_modeling_smoke()
    summary["evaluation"]["train"] = []

    with pytest.raises(
        ValueError,
        match="evaluation metrics for train must be a dict",
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_missing_metric_key() -> None:
    summary = run_baseline_modeling_smoke()
    del summary["evaluation"]["train"]["mae"]

    with pytest.raises(
        ValueError,
        match=r"evaluation metrics for train keys mismatch: .*missing=\['mae'\]",
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_modeling_smoke_summary_rejects_unknown_metric_key() -> None:
    summary = run_baseline_modeling_smoke()
    summary["evaluation"]["train"]["extra_metric"] = 0.0

    with pytest.raises(
        ValueError,
        match=(
            r"evaluation metrics for train keys mismatch: "
            r".*unknown=\['extra_metric'\]"
        ),
    ):
        validate_modeling_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_accepts_valid_summary() -> None:
    summary = run_preprocessing_smoke()

    assert validate_preprocessing_smoke_summary(summary) is summary
    assert set(summary) == PREPROCESSING_SMOKE_SUMMARY_KEYS
    assert set(summary["split_counts"]) == PREPROCESSING_SMOKE_SPLITS
    assert set(summary["split_shape"]) == PREPROCESSING_SMOKE_SPLITS


def test_validate_preprocessing_smoke_summary_rejects_non_dict() -> None:
    with pytest.raises(ValueError, match="preprocessing smoke summary must be a dict"):
        validate_preprocessing_smoke_summary(["not", "a", "dict"])


def test_validate_preprocessing_smoke_summary_rejects_missing_top_level_key() -> None:
    summary = run_preprocessing_smoke()
    del summary["row_count"]

    with pytest.raises(
        ValueError,
        match=r"preprocessing smoke summary keys mismatch: .*missing=\['row_count'\]",
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_unknown_top_level_key() -> None:
    summary = run_preprocessing_smoke()
    summary["unexpected"] = True

    with pytest.raises(
        ValueError,
        match=r"preprocessing smoke summary keys mismatch: .*unknown=\['unexpected'\]",
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_non_dict_split_counts() -> None:
    summary = run_preprocessing_smoke()
    summary["split_counts"] = []

    with pytest.raises(
        ValueError,
        match="preprocessing smoke summary split_counts must be a dict",
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_missing_split_count() -> None:
    summary = run_preprocessing_smoke()
    del summary["split_counts"]["test"]

    with pytest.raises(
        ValueError,
        match=(
            r"preprocessing smoke summary split_counts keys mismatch: "
            r".*missing=\['test'\]"
        ),
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_unknown_split_count() -> None:
    summary = run_preprocessing_smoke()
    summary["split_counts"]["holdout"] = 0

    with pytest.raises(
        ValueError,
        match=(
            r"preprocessing smoke summary split_counts keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_non_dict_split_shape() -> None:
    summary = run_preprocessing_smoke()
    summary["split_shape"] = []

    with pytest.raises(
        ValueError,
        match="preprocessing smoke summary split_shape must be a dict",
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_missing_split_shape() -> None:
    summary = run_preprocessing_smoke()
    del summary["split_shape"]["validation"]

    with pytest.raises(
        ValueError,
        match=(
            r"preprocessing smoke summary split_shape keys mismatch: "
            r".*missing=\['validation'\]"
        ),
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_unknown_split_shape() -> None:
    summary = run_preprocessing_smoke()
    summary["split_shape"]["holdout"] = {"rows": 0, "columns": 4}

    with pytest.raises(
        ValueError,
        match=(
            r"preprocessing smoke summary split_shape keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_non_dict_split_shape_entry() -> None:
    summary = run_preprocessing_smoke()
    summary["split_shape"]["train"] = []

    with pytest.raises(ValueError, match="split_shape for train must be a dict"):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_missing_split_shape_key() -> None:
    summary = run_preprocessing_smoke()
    del summary["split_shape"]["train"]["columns"]

    with pytest.raises(
        ValueError,
        match=r"split_shape for train keys mismatch: .*missing=\['columns'\]",
    ):
        validate_preprocessing_smoke_summary(summary)


def test_validate_preprocessing_smoke_summary_rejects_unknown_split_shape_key() -> None:
    summary = run_preprocessing_smoke()
    summary["split_shape"]["test"]["extra"] = 0

    with pytest.raises(
        ValueError,
        match=r"split_shape for test keys mismatch: .*unknown=\['extra'\]",
    ):
        validate_preprocessing_smoke_summary(summary)
