import numpy as np
import pandas as pd
import pytest

from abc_quant.features.shadow_strength import (
    apply_shadow_strength_score,
    build_shadow_strength_rules,
    evaluate_shadow_strength_holdout,
    strength_monotonicity,
)


def test_shadow_strength_uses_four_equal_weight_rules_and_excludes_raw_inputs() -> None:
    rules = build_shadow_strength_rules(_reference_rows())

    assert len(rules) == 4
    assert {rule.points for rule in rules} == {25}
    assert sum(rule.points for rule in rules) == 100
    assert {rule.feature for rule in rules} == {
        "pre_main_force_net_lots_1d",
        "pre5_upper_tail_count",
        "pre_day_volume_ratio_20",
        "pre_margin_balance_change_5d_pct",
    }
    assert {
        "pre_margin_balance",
        "pre_foreign_net_shares_1d",
        "pre_foreign_net_shares_5d",
    }.isdisjoint(rule.feature for rule in rules)


def test_shadow_strength_blocks_missing_component_instead_of_zero_filling() -> None:
    rows = _scoring_rows()
    rows.loc[1, "pre_margin_balance_change_5d_pct"] = np.nan

    scored = apply_shadow_strength_score(rows, rules=build_shadow_strength_rules(_reference_rows()))

    assert scored.loc[0, "shadow_strength_score"] == pytest.approx(100.0)
    assert scored.loc[0, "shadow_strength_rank_within_signal_date"] == pytest.approx(1.0)
    assert scored.loc[1, "shadow_strength_score_status"] == "INSUFFICIENT_FEATURES"
    assert scored.loc[1, "shadow_strength_missing_components"] == "margin_change"
    assert np.isnan(scored.loc[1, "shadow_strength_score"])
    assert np.isnan(scored.loc[1, "shadow_strength_rank_within_signal_date"])


def test_shadow_strength_rejects_signal_day_source_date() -> None:
    rows = _scoring_rows().iloc[[0]].copy()
    rows.loc[0, "pre_price_source_date"] = rows.loc[0, "asof_date"]

    with pytest.raises(ValueError, match="source is not pre-signal"):
        apply_shadow_strength_score(
            rows,
            rules=build_shadow_strength_rules(_reference_rows()),
        )


def test_forward_outcomes_cannot_change_shadow_strength_score_or_rank() -> None:
    rows = _scoring_rows()
    rows["d5_group"] = ["D5_LOSS", "D5_GAIN_GE_20"]
    rows["d5_adjusted_return_pct"] = [-5.0, 25.0]
    rules = build_shadow_strength_rules(_reference_rows())
    baseline = apply_shadow_strength_score(rows, rules=rules)
    mutated_rows = rows.copy()
    mutated_rows["d5_group"] = ["D5_GAIN_GE_20", "D5_LOSS"]
    mutated_rows["d5_adjusted_return_pct"] = [99.0, -99.0]
    mutated = apply_shadow_strength_score(mutated_rows, rules=rules)

    columns = [
        "shadow_strength_score",
        "shadow_strength_tier",
        "shadow_strength_rank_within_signal_date",
        "shadow_strength_rank_pct_within_signal_date",
    ]
    pd.testing.assert_frame_equal(baseline[columns], mutated[columns])


def test_holdout_cumulative_strength_validation_is_monotonic() -> None:
    scores = [0, 0, 25, 25, 50, 50, 75, 75, 100, 100]
    groups = [
        "D5_LOSS",
        "D5_LOSS",
        "D5_LOSS",
        "D5_LOSS",
        "D5_LOSS",
        "D5_GAIN_10_20",
        "D5_GAIN_10_20",
        "D5_GAIN_GE_20",
        "D5_GAIN_GE_20",
        "D5_GAIN_GE_20",
    ]
    rows = pd.DataFrame(
        {
            "asof_date": pd.date_range("2026-04-01", periods=10, freq="D"),
            "stock_id": [f"{index:04d}" for index in range(10)],
            "d5_group": groups,
            "d5_adjusted_return_pct": [
                -5.0,
                -4.0,
                -3.0,
                -2.0,
                -1.0,
                12.0,
                15.0,
                22.0,
                25.0,
                30.0,
            ],
            "shadow_strength_complete": True,
            "shadow_strength_score": scores,
        }
    )

    validation = evaluate_shadow_strength_holdout(rows, holdout_start="2026-04-01")
    cumulative = validation[validation["view"].eq("cumulative_min_score")]

    assert cumulative["score_threshold"].tolist() == [0.0, 25.0, 50.0, 75.0, 100.0]
    assert strength_monotonicity(validation, view="cumulative_min_score")["all_pass"]
    assert cumulative.iloc[-1]["gain_ge20_lift_vs_complete"] > 1.0


def _reference_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "task": "D5_GAIN_GE10_VS_LOSS",
                "feature": "pre_main_force_net_lots_1d",
                "direction": "HIGHER",
                "threshold": 7.5,
                "discovery_end": "2026-03-31",
            },
            {
                "task": "D5_GAIN_GE10_VS_LOSS",
                "feature": "pre5_upper_tail_count",
                "direction": "LOWER",
                "threshold": 0.5,
                "discovery_end": "2026-03-31",
            },
            {
                "task": "D5_GAIN_GE10_VS_LOSS",
                "feature": "pre_day_volume_ratio_20",
                "direction": "HIGHER",
                "threshold": 0.7,
                "discovery_end": "2026-03-31",
            },
            {
                "task": "D5_GAIN_GE10_VS_LOSS",
                "feature": "pre_margin_balance_change_5d_pct",
                "direction": "HIGHER",
                "threshold": 0.0,
                "discovery_end": "2026-03-31",
            },
        ]
    )


def _scoring_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asof_date": ["2026-04-01", "2026-04-01"],
            "stock_id": ["2330", "2317"],
            "pre_main_force_net_lots_1d": [10.0, 0.0],
            "pre_main_force_source_date": ["2026-03-31", "2026-03-31"],
            "pre5_upper_tail_count": [0.0, 1.0],
            "pre_price_source_date": ["2026-03-31", "2026-03-31"],
            "pre_day_volume_ratio_20": [1.0, 0.5],
            "pre_margin_balance_change_5d_pct": [1.0, -1.0],
            "pre_margin_available_date": ["2026-03-31", "2026-03-31"],
        }
    )
