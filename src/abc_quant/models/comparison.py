"""Prediction evaluation comparison contracts."""

from __future__ import annotations

from dataclasses import dataclass

from abc_quant.models.evaluation import (
    PredictionEvaluationResult,
    SplitPredictionBundleEvaluationResult,
)


@dataclass(frozen=True)
class SplitEvaluationComparison:
    """Candidate-minus-reference metric deltas for one evaluated split."""

    split_name: str
    reference_name: str
    candidate_name: str
    row_count: int
    non_missing_count: int
    missing_actual_count: int
    mae_delta: float
    rmse_delta: float
    mean_error_delta: float
    prediction_mean_delta: float


@dataclass(frozen=True)
class PredictionEvaluationComparison:
    """Train/validation/test comparison of two evaluated prediction bundles."""

    reference_name: str
    candidate_name: str
    train: SplitEvaluationComparison
    validation: SplitEvaluationComparison
    test: SplitEvaluationComparison


def compare_prediction_evaluations(
    reference: SplitPredictionBundleEvaluationResult,
    candidate: SplitPredictionBundleEvaluationResult,
    *,
    reference_name: str = "reference",
    candidate_name: str = "candidate",
) -> PredictionEvaluationComparison:
    """Compare two already-computed prediction-bundle evaluations.

    This function computes candidate-minus-reference deltas for diagnostic
    metrics only. It does not refit models, recompute predictions, rank models,
    create strategy signals, define allocation logic, build performance curves,
    or run simulation engines.
    """
    if not isinstance(reference, SplitPredictionBundleEvaluationResult):
        raise TypeError("reference must be a SplitPredictionBundleEvaluationResult")
    if not isinstance(candidate, SplitPredictionBundleEvaluationResult):
        raise TypeError("candidate must be a SplitPredictionBundleEvaluationResult")

    normalized_reference_name = _normalize_name(reference_name, "reference_name")
    normalized_candidate_name = _normalize_name(candidate_name, "candidate_name")

    return PredictionEvaluationComparison(
        reference_name=normalized_reference_name,
        candidate_name=normalized_candidate_name,
        train=_compare_split(
            reference.train,
            candidate.train,
            split_name="train",
            reference_name=normalized_reference_name,
            candidate_name=normalized_candidate_name,
        ),
        validation=_compare_split(
            reference.validation,
            candidate.validation,
            split_name="validation",
            reference_name=normalized_reference_name,
            candidate_name=normalized_candidate_name,
        ),
        test=_compare_split(
            reference.test,
            candidate.test,
            split_name="test",
            reference_name=normalized_reference_name,
            candidate_name=normalized_candidate_name,
        ),
    )


def _compare_split(
    reference: PredictionEvaluationResult,
    candidate: PredictionEvaluationResult,
    *,
    split_name: str,
    reference_name: str,
    candidate_name: str,
) -> SplitEvaluationComparison:
    if not isinstance(reference, PredictionEvaluationResult):
        raise TypeError(f"{split_name} reference must be a PredictionEvaluationResult")
    if not isinstance(candidate, PredictionEvaluationResult):
        raise TypeError(f"{split_name} candidate must be a PredictionEvaluationResult")

    _require_matching_count(reference, candidate, split_name, "row_count")
    _require_matching_count(reference, candidate, split_name, "non_missing_count")
    _require_matching_count(reference, candidate, split_name, "missing_actual_count")

    return SplitEvaluationComparison(
        split_name=split_name,
        reference_name=reference_name,
        candidate_name=candidate_name,
        row_count=reference.row_count,
        non_missing_count=reference.non_missing_count,
        missing_actual_count=reference.missing_actual_count,
        mae_delta=float(candidate.mae - reference.mae),
        rmse_delta=float(candidate.rmse - reference.rmse),
        mean_error_delta=float(candidate.mean_error - reference.mean_error),
        prediction_mean_delta=float(
            candidate.prediction_mean - reference.prediction_mean
        ),
    )


def _require_matching_count(
    reference: PredictionEvaluationResult,
    candidate: PredictionEvaluationResult,
    split_name: str,
    field_name: str,
) -> None:
    reference_value = getattr(reference, field_name)
    candidate_value = getattr(candidate, field_name)
    if reference_value != candidate_value:
        raise ValueError(
            f"{split_name} {field_name} mismatch: "
            f"reference={reference_value}; candidate={candidate_value}"
        )


def _normalize_name(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()
