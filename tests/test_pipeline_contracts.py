from __future__ import annotations

from copy import deepcopy

import pytest

from abc_quant.pipeline.contracts import (
    EVALUATION_METRIC_KEYS,
    LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS,
    LINEAR_REGRESSION_SMOKE_SPLITS,
    LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS,
    MODEL_COMPARISON_SMOKE_COMPARISON_KEYS,
    MODEL_COMPARISON_SMOKE_MODEL_KEYS,
    MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS,
    MODEL_COMPARISON_SMOKE_SPLITS,
    MODEL_COMPARISON_SMOKE_SUMMARY_KEYS,
    MODELING_SMOKE_SUMMARY_KEYS,
    PREPROCESSING_SMOKE_SPLITS,
    PREPROCESSING_SMOKE_SUMMARY_KEYS,
    SUPERVISED_DATASET_SMOKE_SPLITS,
    SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS,
    validate_linear_regression_smoke_summary,
    validate_model_comparison_smoke_summary,
    validate_modeling_smoke_summary,
    validate_preprocessing_smoke_summary,
    validate_supervised_dataset_smoke_summary,
)
from abc_quant.pipeline.linear_modeling import run_linear_regression_smoke
from abc_quant.pipeline.model_comparison import run_model_comparison_smoke
from abc_quant.pipeline.modeling import run_baseline_modeling_smoke
from abc_quant.pipeline.preprocessing import run_preprocessing_smoke
from abc_quant.pipeline.supervised import run_supervised_dataset_smoke


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


def test_validate_linear_regression_smoke_summary_accepts_valid_summary() -> None:
    summary = run_linear_regression_smoke()

    assert validate_linear_regression_smoke_summary(summary) is summary
    assert set(summary) == LINEAR_REGRESSION_SMOKE_SUMMARY_KEYS
    assert set(summary["split_counts_after_label_drop"]) == (
        LINEAR_REGRESSION_SMOKE_SPLITS
    )
    assert set(summary["dropped_label_counts"]) == LINEAR_REGRESSION_SMOKE_SPLITS
    assert set(summary["prediction_counts"]) == LINEAR_REGRESSION_SMOKE_SPLITS
    assert set(summary["evaluation"]) == LINEAR_REGRESSION_SMOKE_SPLITS
    assert set(summary["evaluation"]["train"]) == (
        LINEAR_REGRESSION_SMOKE_EVALUATION_KEYS
    )


def test_validate_linear_regression_smoke_summary_rejects_non_dict() -> None:
    with pytest.raises(
        ValueError,
        match="linear regression smoke summary must be a dict",
    ):
        validate_linear_regression_smoke_summary(["not", "a", "dict"])


def test_validate_linear_regression_smoke_summary_rejects_missing_top_level_key() -> None:
    summary = run_linear_regression_smoke()
    del summary["row_count"]

    with pytest.raises(
        ValueError,
        match=(
            r"linear regression smoke summary keys mismatch: "
            r".*missing=\['row_count'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_unknown_top_level_key() -> None:
    summary = run_linear_regression_smoke()
    summary["unexpected"] = True

    with pytest.raises(
        ValueError,
        match=(
            r"linear regression smoke summary keys mismatch: "
            r".*unknown=\['unexpected'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_non_list_features() -> None:
    summary = run_linear_regression_smoke()
    summary["feature_columns"] = tuple(summary["feature_columns"])

    with pytest.raises(
        ValueError,
        match="linear regression smoke summary feature_columns must be a list",
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_non_dict_coefficients() -> None:
    summary = run_linear_regression_smoke()
    summary["coefficients"] = []

    with pytest.raises(
        ValueError,
        match="linear regression smoke summary coefficients must be a dict",
    ):
        validate_linear_regression_smoke_summary(summary)


@pytest.mark.parametrize(
    "summary_key",
    [
        "split_counts_after_label_drop",
        "dropped_label_counts",
        "prediction_counts",
    ],
)
def test_validate_linear_regression_smoke_summary_rejects_non_dict_split_mapping(
    summary_key: str,
) -> None:
    summary = run_linear_regression_smoke()
    summary[summary_key] = []

    with pytest.raises(
        ValueError,
        match=f"linear regression smoke summary {summary_key} must be a dict",
    ):
        validate_linear_regression_smoke_summary(summary)


@pytest.mark.parametrize(
    "summary_key",
    [
        "split_counts_after_label_drop",
        "dropped_label_counts",
        "prediction_counts",
    ],
)
def test_validate_linear_regression_smoke_summary_rejects_missing_split_mapping(
    summary_key: str,
) -> None:
    summary = run_linear_regression_smoke()
    del summary[summary_key]["test"]

    with pytest.raises(
        ValueError,
        match=(
            rf"linear regression smoke summary {summary_key} keys mismatch: "
            r".*missing=\['test'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


@pytest.mark.parametrize(
    "summary_key",
    [
        "split_counts_after_label_drop",
        "dropped_label_counts",
        "prediction_counts",
    ],
)
def test_validate_linear_regression_smoke_summary_rejects_unknown_split_mapping(
    summary_key: str,
) -> None:
    summary = run_linear_regression_smoke()
    summary[summary_key]["holdout"] = 0

    with pytest.raises(
        ValueError,
        match=(
            rf"linear regression smoke summary {summary_key} keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_non_dict_evaluation() -> None:
    summary = run_linear_regression_smoke()
    summary["evaluation"] = []

    with pytest.raises(
        ValueError,
        match="linear regression smoke summary evaluation must be a dict",
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_missing_evaluation_split() -> None:
    summary = run_linear_regression_smoke()
    del summary["evaluation"]["validation"]

    with pytest.raises(
        ValueError,
        match=(
            r"linear regression smoke summary evaluation keys mismatch: "
            r".*missing=\['validation'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_unknown_evaluation_split() -> None:
    summary = run_linear_regression_smoke()
    summary["evaluation"]["holdout"] = deepcopy(summary["evaluation"]["test"])

    with pytest.raises(
        ValueError,
        match=(
            r"linear regression smoke summary evaluation keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_non_dict_metrics() -> None:
    summary = run_linear_regression_smoke()
    summary["evaluation"]["train"] = []

    with pytest.raises(
        ValueError,
        match="linear regression metrics for train must be a dict",
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_missing_metric_key() -> None:
    summary = run_linear_regression_smoke()
    del summary["evaluation"]["test"]["rmse"]

    with pytest.raises(
        ValueError,
        match=r"linear regression metrics for test keys mismatch: .*missing=\['rmse'\]",
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_linear_regression_smoke_summary_rejects_unknown_metric_key() -> None:
    summary = run_linear_regression_smoke()
    summary["evaluation"]["validation"]["extra_metric"] = 0.0

    with pytest.raises(
        ValueError,
        match=(
            r"linear regression metrics for validation keys mismatch: "
            r".*unknown=\['extra_metric'\]"
        ),
    ):
        validate_linear_regression_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_accepts_valid_summary() -> None:
    summary = run_model_comparison_smoke()

    assert validate_model_comparison_smoke_summary(summary) is summary
    assert set(summary) == MODEL_COMPARISON_SMOKE_SUMMARY_KEYS
    assert set(summary["reference_model"]) == MODEL_COMPARISON_SMOKE_MODEL_KEYS
    assert set(summary["candidate_model"]) == MODEL_COMPARISON_SMOKE_MODEL_KEYS
    assert set(summary["split_counts"]) == MODEL_COMPARISON_SMOKE_SPLITS
    assert set(summary["dropped_label_counts"]) == MODEL_COMPARISON_SMOKE_SPLITS
    assert set(summary["reference_evaluation"]) == (
        MODEL_COMPARISON_SMOKE_MODEL_KEYS | MODEL_COMPARISON_SMOKE_SPLITS
    )
    assert set(summary["candidate_evaluation"]) == (
        MODEL_COMPARISON_SMOKE_MODEL_KEYS | MODEL_COMPARISON_SMOKE_SPLITS
    )
    assert set(summary["reference_evaluation"]["train"]) == EVALUATION_METRIC_KEYS
    assert set(summary["candidate_evaluation"]["test"]) == EVALUATION_METRIC_KEYS
    assert set(summary["comparison"]) == MODEL_COMPARISON_SMOKE_COMPARISON_KEYS
    assert set(summary["comparison"]["train"]) == (
        MODEL_COMPARISON_SMOKE_SPLIT_COMPARISON_KEYS
    )


def test_validate_model_comparison_smoke_summary_rejects_non_dict() -> None:
    with pytest.raises(
        ValueError,
        match="model comparison smoke summary must be a dict",
    ):
        validate_model_comparison_smoke_summary(["not", "a", "dict"])


def test_validate_model_comparison_smoke_summary_rejects_missing_top_level_key() -> None:
    summary = run_model_comparison_smoke()
    del summary["row_count"]

    with pytest.raises(
        ValueError,
        match=(
            r"model comparison smoke summary keys mismatch: "
            r".*missing=\['row_count'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_unknown_top_level_key() -> None:
    summary = run_model_comparison_smoke()
    summary["unexpected"] = True

    with pytest.raises(
        ValueError,
        match=(
            r"model comparison smoke summary keys mismatch: "
            r".*unknown=\['unexpected'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize("metadata_key", ["reference_model", "candidate_model"])
def test_validate_model_comparison_smoke_summary_rejects_non_dict_model_metadata(
    metadata_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[metadata_key] = []

    with pytest.raises(
        ValueError,
        match=f"model comparison smoke summary {metadata_key} must be a dict",
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize("metadata_key", ["reference_model", "candidate_model"])
def test_validate_model_comparison_smoke_summary_rejects_missing_model_metadata_key(
    metadata_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    del summary[metadata_key]["method"]

    with pytest.raises(
        ValueError,
        match=(
            rf"model comparison smoke summary {metadata_key} keys mismatch: "
            r".*missing=\['method'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize("metadata_key", ["reference_model", "candidate_model"])
def test_validate_model_comparison_smoke_summary_rejects_unknown_model_metadata_key(
    metadata_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[metadata_key]["display_name"] = "extra"

    with pytest.raises(
        ValueError,
        match=(
            rf"model comparison smoke summary {metadata_key} keys mismatch: "
            r".*unknown=\['display_name'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize("summary_key", ["split_counts", "dropped_label_counts"])
def test_validate_model_comparison_smoke_summary_rejects_non_dict_split_mapping(
    summary_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[summary_key] = []

    with pytest.raises(
        ValueError,
        match=f"model comparison smoke summary {summary_key} must be a dict",
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize("summary_key", ["split_counts", "dropped_label_counts"])
def test_validate_model_comparison_smoke_summary_rejects_missing_split_mapping(
    summary_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    del summary[summary_key]["test"]

    with pytest.raises(
        ValueError,
        match=(
            rf"model comparison smoke summary {summary_key} keys mismatch: "
            r".*missing=\['test'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize("summary_key", ["split_counts", "dropped_label_counts"])
def test_validate_model_comparison_smoke_summary_rejects_unknown_split_mapping(
    summary_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[summary_key]["holdout"] = 0

    with pytest.raises(
        ValueError,
        match=(
            rf"model comparison smoke summary {summary_key} keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize(
    "evaluation_key",
    ["reference_evaluation", "candidate_evaluation"],
)
def test_validate_model_comparison_smoke_summary_rejects_non_dict_evaluation(
    evaluation_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[evaluation_key] = []

    with pytest.raises(
        ValueError,
        match=f"model comparison smoke summary {evaluation_key} must be a dict",
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize(
    "evaluation_key",
    ["reference_evaluation", "candidate_evaluation"],
)
def test_validate_model_comparison_smoke_summary_rejects_missing_evaluation_split(
    evaluation_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    del summary[evaluation_key]["validation"]

    with pytest.raises(
        ValueError,
        match=(
            rf"model comparison smoke summary {evaluation_key} keys mismatch: "
            r".*missing=\['validation'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize(
    "evaluation_key",
    ["reference_evaluation", "candidate_evaluation"],
)
def test_validate_model_comparison_smoke_summary_rejects_unknown_evaluation_split(
    evaluation_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[evaluation_key]["holdout"] = deepcopy(summary[evaluation_key]["test"])

    with pytest.raises(
        ValueError,
        match=(
            rf"model comparison smoke summary {evaluation_key} keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize(
    "evaluation_key",
    ["reference_evaluation", "candidate_evaluation"],
)
def test_validate_model_comparison_smoke_summary_rejects_non_dict_metrics(
    evaluation_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[evaluation_key]["train"] = []

    with pytest.raises(
        ValueError,
        match=f"{evaluation_key} metrics for train must be a dict",
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize(
    "evaluation_key",
    ["reference_evaluation", "candidate_evaluation"],
)
def test_validate_model_comparison_smoke_summary_rejects_missing_metric_key(
    evaluation_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    del summary[evaluation_key]["test"]["mae"]

    with pytest.raises(
        ValueError,
        match=rf"{evaluation_key} metrics for test keys mismatch: .*missing=\['mae'\]",
    ):
        validate_model_comparison_smoke_summary(summary)


@pytest.mark.parametrize(
    "evaluation_key",
    ["reference_evaluation", "candidate_evaluation"],
)
def test_validate_model_comparison_smoke_summary_rejects_unknown_metric_key(
    evaluation_key: str,
) -> None:
    summary = run_model_comparison_smoke()
    summary[evaluation_key]["validation"]["extra_metric"] = 0.0

    with pytest.raises(
        ValueError,
        match=(
            rf"{evaluation_key} metrics for validation keys mismatch: "
            r".*unknown=\['extra_metric'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_non_dict_comparison() -> None:
    summary = run_model_comparison_smoke()
    summary["comparison"] = []

    with pytest.raises(
        ValueError,
        match="model comparison smoke summary comparison must be a dict",
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_missing_comparison_key() -> None:
    summary = run_model_comparison_smoke()
    del summary["comparison"]["candidate_name"]

    with pytest.raises(
        ValueError,
        match=(
            r"model comparison smoke summary comparison keys mismatch: "
            r".*missing=\['candidate_name'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_unknown_comparison_key() -> None:
    summary = run_model_comparison_smoke()
    summary["comparison"]["winner"] = "candidate"

    with pytest.raises(
        ValueError,
        match=(
            r"model comparison smoke summary comparison keys mismatch: "
            r".*unknown=\['winner'\]"
        ),
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_non_dict_split_comparison() -> None:
    summary = run_model_comparison_smoke()
    summary["comparison"]["train"] = []

    with pytest.raises(
        ValueError,
        match="comparison for train must be a dict",
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_missing_split_comparison_key() -> None:
    summary = run_model_comparison_smoke()
    del summary["comparison"]["test"]["mae_delta"]

    with pytest.raises(
        ValueError,
        match=r"comparison for test keys mismatch: .*missing=\['mae_delta'\]",
    ):
        validate_model_comparison_smoke_summary(summary)


def test_validate_model_comparison_smoke_summary_rejects_unknown_split_comparison_key() -> None:
    summary = run_model_comparison_smoke()
    summary["comparison"]["validation"]["rank"] = 1

    with pytest.raises(
        ValueError,
        match=r"comparison for validation keys mismatch: .*unknown=\['rank'\]",
    ):
        validate_model_comparison_smoke_summary(summary)


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


def test_validate_supervised_dataset_smoke_summary_accepts_valid_summary() -> None:
    summary = run_supervised_dataset_smoke()

    assert validate_supervised_dataset_smoke_summary(summary) is summary
    assert set(summary) == SUPERVISED_DATASET_SMOKE_SUMMARY_KEYS
    assert set(summary["split_counts_before_label_drop"]) == (
        SUPERVISED_DATASET_SMOKE_SPLITS
    )
    assert set(summary["split_counts_after_label_drop"]) == (
        SUPERVISED_DATASET_SMOKE_SPLITS
    )
    assert set(summary["dropped_label_counts"]) == SUPERVISED_DATASET_SMOKE_SPLITS
    assert set(summary["split_shape"]) == SUPERVISED_DATASET_SMOKE_SPLITS


def test_validate_supervised_dataset_smoke_summary_rejects_non_dict() -> None:
    with pytest.raises(
        ValueError,
        match="supervised dataset smoke summary must be a dict",
    ):
        validate_supervised_dataset_smoke_summary(["not", "a", "dict"])


def test_validate_supervised_dataset_smoke_summary_rejects_missing_top_level_key() -> None:
    summary = run_supervised_dataset_smoke()
    del summary["row_count"]

    with pytest.raises(
        ValueError,
        match=(
            r"supervised dataset smoke summary keys mismatch: "
            r".*missing=\['row_count'\]"
        ),
    ):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_unknown_top_level_key() -> None:
    summary = run_supervised_dataset_smoke()
    summary["unexpected"] = True

    with pytest.raises(
        ValueError,
        match=(
            r"supervised dataset smoke summary keys mismatch: "
            r".*unknown=\['unexpected'\]"
        ),
    ):
        validate_supervised_dataset_smoke_summary(summary)


@pytest.mark.parametrize(
    "summary_key",
    [
        "split_counts_before_label_drop",
        "split_counts_after_label_drop",
        "dropped_label_counts",
    ],
)
def test_validate_supervised_dataset_smoke_summary_rejects_non_dict_split_counts(
    summary_key: str,
) -> None:
    summary = run_supervised_dataset_smoke()
    summary[summary_key] = []

    with pytest.raises(
        ValueError,
        match=f"supervised dataset smoke summary {summary_key} must be a dict",
    ):
        validate_supervised_dataset_smoke_summary(summary)


@pytest.mark.parametrize(
    "summary_key",
    [
        "split_counts_before_label_drop",
        "split_counts_after_label_drop",
        "dropped_label_counts",
    ],
)
def test_validate_supervised_dataset_smoke_summary_rejects_missing_split_key(
    summary_key: str,
) -> None:
    summary = run_supervised_dataset_smoke()
    del summary[summary_key]["test"]

    with pytest.raises(
        ValueError,
        match=(
            rf"supervised dataset smoke summary {summary_key} keys mismatch: "
            r".*missing=\['test'\]"
        ),
    ):
        validate_supervised_dataset_smoke_summary(summary)


@pytest.mark.parametrize(
    "summary_key",
    [
        "split_counts_before_label_drop",
        "split_counts_after_label_drop",
        "dropped_label_counts",
    ],
)
def test_validate_supervised_dataset_smoke_summary_rejects_unknown_split_key(
    summary_key: str,
) -> None:
    summary = run_supervised_dataset_smoke()
    summary[summary_key]["holdout"] = 0

    with pytest.raises(
        ValueError,
        match=(
            rf"supervised dataset smoke summary {summary_key} keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_non_dict_split_shape() -> None:
    summary = run_supervised_dataset_smoke()
    summary["split_shape"] = []

    with pytest.raises(
        ValueError,
        match="supervised dataset smoke summary split_shape must be a dict",
    ):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_missing_split_shape() -> None:
    summary = run_supervised_dataset_smoke()
    del summary["split_shape"]["validation"]

    with pytest.raises(
        ValueError,
        match=(
            r"supervised dataset smoke summary split_shape keys mismatch: "
            r".*missing=\['validation'\]"
        ),
    ):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_unknown_split_shape() -> None:
    summary = run_supervised_dataset_smoke()
    summary["split_shape"]["holdout"] = {"rows": 0, "columns": 4}

    with pytest.raises(
        ValueError,
        match=(
            r"supervised dataset smoke summary split_shape keys mismatch: "
            r".*unknown=\['holdout'\]"
        ),
    ):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_malformed_shape() -> None:
    summary = run_supervised_dataset_smoke()
    summary["split_shape"]["train"] = []

    with pytest.raises(ValueError, match="split_shape for train must be a dict"):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_missing_shape_key() -> None:
    summary = run_supervised_dataset_smoke()
    del summary["split_shape"]["train"]["columns"]

    with pytest.raises(
        ValueError,
        match=r"split_shape for train keys mismatch: .*missing=\['columns'\]",
    ):
        validate_supervised_dataset_smoke_summary(summary)


def test_validate_supervised_dataset_smoke_summary_rejects_unknown_shape_key() -> None:
    summary = run_supervised_dataset_smoke()
    summary["split_shape"]["test"]["extra"] = 0

    with pytest.raises(
        ValueError,
        match=r"split_shape for test keys mismatch: .*unknown=\['extra'\]",
    ):
        validate_supervised_dataset_smoke_summary(summary)
