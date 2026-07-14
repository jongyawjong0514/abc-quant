from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from abc_quant.validation.forward_outcome_surface import (
    CLASS_PROBABILITY_COLUMNS,
    MODE,
    OUTCOME_CLASSES,
    TAIL_PROBABILITY_COLUMN,
    assert_probability_surface,
    build_forward_outcomes,
    build_monotone_probability_surface,
    evaluate_forward_probability_surface,
    find_label_leakage_columns,
)


def _build_surface(raw: pd.DataFrame, *, include_tail: bool = True) -> pd.DataFrame:
    return build_monotone_probability_surface(
        raw,
        raw_p_gt0_column="raw_gt0",
        raw_p_ge10_column="raw_ge10",
        raw_p_ge20_column="raw_ge20",
        raw_tail_loss_column="raw_tail" if include_tail else None,
    )


def test_forward_outcome_boundaries_are_exhaustive_and_tail_is_separate() -> None:
    returns = pd.Series(
        [-3.1, -3.0, -0.01, 0.0, 9.999, 10.0, 19.999, 20.0, np.nan, np.inf],
        index=list("abcdefghij"),
    )

    outcomes = build_forward_outcomes(returns)

    assert outcomes["outcome_class"].tolist() == [
        "loss_lt_0",
        "loss_lt_0",
        "loss_lt_0",
        "gain_0_10",
        "gain_0_10",
        "gain_10_20",
        "gain_10_20",
        "gain_ge_20",
        pd.NA,
        pd.NA,
    ]
    assert outcomes.loc["a":"h", list(OUTCOME_CLASSES)].astype(int).sum(axis=1).eq(1).all()
    assert outcomes.loc[["i", "j"], list(OUTCOME_CLASSES)].isna().all(axis=None)
    assert outcomes.loc["a", "tail_loss_le_minus3"]
    assert outcomes.loc["b", "tail_loss_le_minus3"]
    assert not outcomes.loc["c", "tail_loss_le_minus3"]
    assert pd.isna(outcomes.loc["i", "tail_loss_le_minus3"])
    assert outcomes["mode"].eq(MODE).all()
    assert not outcomes["formal_trade_effect"].any()


def test_probability_projection_enforces_order_bounds_and_missingness() -> None:
    raw = pd.DataFrame(
        {
            "raw_gt0": [0.9, 0.2, 1.2, 0.8],
            "raw_ge10": [0.7, 0.8, -0.1, np.nan],
            "raw_ge20": [0.2, 0.7, 0.5, 0.2],
            "raw_tail": [-0.1, 1.3, np.nan, 0.4],
        },
        index=["ordered", "pooled", "clipped", "missing"],
    )

    surface = _build_surface(raw)

    assert surface.loc["ordered", ["p_gt0", "p_ge10", "p_ge20"]].tolist() == pytest.approx(
        [0.9, 0.7, 0.2]
    )
    assert surface.loc["pooled", ["p_gt0", "p_ge10", "p_ge20"]].tolist() == pytest.approx(
        [0.5666666667, 0.5666666667, 0.5666666667]
    )
    assert surface.loc["clipped", ["p_gt0", "p_ge10", "p_ge20"]].tolist() == pytest.approx(
        [1.0, 0.25, 0.25]
    )
    assert surface.loc["missing", ["p_gt0", "p_ge10", "p_ge20"]].isna().all()
    assert surface.loc["missing", list(CLASS_PROBABILITY_COLUMNS)].isna().all()
    assert not surface.loc["missing", "probability_surface_complete"]
    assert surface.loc["missing", TAIL_PROBABILITY_COLUMN] == pytest.approx(0.4)
    assert surface.loc["ordered", TAIL_PROBABILITY_COLUMN] == pytest.approx(0.0)
    assert surface.loc["pooled", TAIL_PROBABILITY_COLUMN] == pytest.approx(1.0)
    assert pd.isna(surface.loc["clipped", TAIL_PROBABILITY_COLUMN])

    complete = surface["probability_surface_complete"]
    cumulative = surface.loc[complete, ["p_gt0", "p_ge10", "p_ge20"]]
    assert cumulative["p_ge20"].le(cumulative["p_ge10"]).all()
    assert cumulative["p_ge10"].le(cumulative["p_gt0"]).all()
    assert surface.loc[complete, list(CLASS_PROBABILITY_COLUMNS)].sum(axis=1).eq(1.0).all()
    assert not surface["formal_trade_effect"].any()
    assert_probability_surface(surface)


def test_three_column_surface_keeps_tail_missing_instead_of_zero() -> None:
    raw = pd.DataFrame(
        {"raw_gt0": [0.8], "raw_ge10": [0.4], "raw_ge20": [0.1]},
        index=["sample"],
    )

    surface = _build_surface(raw, include_tail=False)

    assert pd.isna(surface.loc["sample", TAIL_PROBABILITY_COLUMN])
    assert not surface.loc["sample", "tail_probability_available"]
    assert surface.loc["sample", "probability_surface_complete"]


@pytest.mark.parametrize(
    ("column", "values", "message"),
    [
        ("p_ge10", [0.9], "violates"),
        ("p_gt0", [1.1], "within"),
    ],
)
def test_probability_surface_rejects_invalid_values(
    column: str,
    values: list[float],
    message: str,
) -> None:
    surface = pd.DataFrame({"p_gt0": [0.8], "p_ge10": [0.4], "p_ge20": [0.1]})
    surface[column] = values

    with pytest.raises(ValueError, match=message):
        assert_probability_surface(surface)


def test_probability_surface_rejects_partial_missing_and_formal_effect() -> None:
    partial = pd.DataFrame({"p_gt0": [0.8], "p_ge10": [np.nan], "p_ge20": [0.1]})
    with pytest.raises(ValueError, match="complete or entirely missing"):
        assert_probability_surface(partial)

    formal = pd.DataFrame(
        {
            "p_gt0": [0.8],
            "p_ge10": [0.4],
            "p_ge20": [0.1],
            "mode": [MODE],
            "formal_trade_effect": [True],
        }
    )
    with pytest.raises(ValueError, match="formal trade effect"):
        assert_probability_surface(formal)


def test_evaluator_reports_perfect_metrics_for_all_four_targets() -> None:
    returns = pd.Series([-4.0, 5.0, 15.0, 25.0], index=list("abcd"))
    raw = pd.DataFrame(
        {
            "raw_gt0": [0.0, 1.0, 1.0, 1.0],
            "raw_ge10": [0.0, 0.0, 1.0, 1.0],
            "raw_ge20": [0.0, 0.0, 0.0, 1.0],
            "raw_tail": [1.0, 0.0, 0.0, 0.0],
        },
        index=returns.index,
    )

    metrics = evaluate_forward_probability_surface(returns, _build_surface(raw))

    assert metrics["target"].tolist() == [
        "non_loss_ge_0",
        "gain_ge_10",
        "gain_ge_20",
        "tail_loss_le_minus3",
    ]
    assert metrics["universe_rows"].eq(4).all()
    assert metrics["label_rows"].eq(4).all()
    assert metrics["evaluation_rows"].eq(4).all()
    assert metrics["coverage"].eq(1.0).all()
    assert metrics["brier"].eq(0.0).all()
    assert metrics["calibration_gap"].eq(0.0).all()
    assert metrics["logloss"].lt(2e-12).all()
    assert not metrics["empty_universe"].any()
    assert not metrics["empty_evaluation"].any()
    assert not metrics["formal_trade_effect"].any()


def test_evaluator_coverage_excludes_missing_predictions_without_imputation() -> None:
    returns = pd.Series([-4.0, 5.0, 15.0], index=[10, 11, 12])
    raw = pd.DataFrame(
        {
            "raw_gt0": [0.0, np.nan, 1.0],
            "raw_ge10": [0.0, np.nan, 1.0],
            "raw_ge20": [0.0, np.nan, 0.0],
            "raw_tail": [1.0, np.nan, 0.0],
        },
        index=returns.index,
    )

    metrics = evaluate_forward_probability_surface(returns, _build_surface(raw))

    assert metrics["prediction_rows"].eq(2).all()
    assert metrics["evaluation_rows"].eq(2).all()
    assert metrics["coverage"].eq(2 / 3).all()
    assert not metrics["empty_evaluation"].any()


def test_evaluator_reports_empty_universe_without_fabricating_scores() -> None:
    raw = pd.DataFrame(columns=["raw_gt0", "raw_ge10", "raw_ge20", "raw_tail"])
    surface = _build_surface(raw)

    metrics = evaluate_forward_probability_surface(pd.Series(dtype=float), surface)

    assert len(metrics) == 4
    assert metrics["universe_rows"].eq(0).all()
    assert metrics["label_rows"].eq(0).all()
    assert metrics["evaluation_rows"].eq(0).all()
    assert metrics["coverage"].eq(0.0).all()
    assert metrics["empty_universe"].all()
    assert metrics["empty_evaluation"].all()
    assert metrics[["brier", "logloss", "calibration_gap"]].isna().all(axis=None)


@pytest.mark.parametrize(
    "leaked_column",
    ["future_d5_net_return_pct", "target_gain_ge10", "outcome_class"],
)
def test_evaluator_rejects_label_leakage_columns(leaked_column: str) -> None:
    returns = pd.Series([1.0])
    raw = pd.DataFrame(
        {"raw_gt0": [0.8], "raw_ge10": [0.3], "raw_ge20": [0.1], "raw_tail": [0.2]}
    )
    surface = _build_surface(raw)
    surface[leaked_column] = [1.0]

    assert find_label_leakage_columns(surface.columns) == [leaked_column]
    with pytest.raises(ValueError, match="label leakage"):
        evaluate_forward_probability_surface(returns, surface)


def test_evaluator_requires_exact_index_alignment() -> None:
    returns = pd.Series([1.0], index=["return-row"])
    raw = pd.DataFrame(
        {"raw_gt0": [0.8], "raw_ge10": [0.3], "raw_ge20": [0.1], "raw_tail": [0.2]},
        index=["prediction-row"],
    )

    with pytest.raises(ValueError, match="index must exactly match"):
        evaluate_forward_probability_surface(returns, _build_surface(raw))
