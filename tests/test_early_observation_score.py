import pandas as pd
import pytest

from abc_quant.features.early_observation_score import (
    EarlyObservationComponent,
    EarlyObservationScoreConfig,
    score_early_observation,
)


def test_complete_four_stage_path_scores_early_evidence_and_confirmation_separately() -> None:
    result = score_early_observation(_positive_stages())

    assert result.stage == "D_CONFIRMATION_REVIEW"
    assert result.score == 100.0
    assert result.early_score == 100.0
    assert result.confirmation_score == 100.0
    assert result.confirmation_status == "CONFIRMED"
    assert result.confirmed is True
    assert result.eligibility == "SHADOW_WATCH_ELIGIBLE"
    assert result.mode == "shadow_observation_only"
    assert result.formal_trade_effect is False
    assert _component(result.components, "selling_pressure_contraction").reason == (
        "low_volume_bullish_context"
    )
    assert _component(result.components, "pressure_breakout_confirmation").points == 0.0


def test_volume_and_tight_body_boundaries_pass_in_positive_context() -> None:
    stages = _positive_stages()
    stages["D-5"]["volume_ratio_20"] = 0.50
    stages["D-5"]["volume_ratio_slope"] = 0.0
    stages["D-5"]["pre5_min_abs_open_close_pct"] = 1.2

    result = score_early_observation(stages)

    contraction = _component(result.components, "selling_pressure_contraction")
    compression = _component(result.components, "tight_body_compression")
    assert contraction.passed is True
    assert compression.passed is True
    assert compression.points == 5.0
    assert compression.evidence_status == "unstable_context_only"


def test_one_tight_body_in_preceding_five_days_is_conditional_bonus() -> None:
    stages = _positive_stages()
    stages["D-5"].pop("pre5_min_abs_open_close_pct")
    stages["D-5"]["pre5_abs_open_close_pct"] = [2.1, 1.8, 1.2, 2.4, 1.7]

    result = score_early_observation(stages)

    compression = _component(result.components, "tight_body_compression")
    assert compression.passed is True
    assert compression.evidence_status == "unstable_context_only"


@pytest.mark.parametrize(
    ("risk_field", "risk_value"),
    [
        ("long_upper_shadow", True),
        ("persistent_price_decline", True),
    ],
)
def test_tight_body_with_supply_or_continuing_decline_is_no_demand_risk(
    risk_field: str,
    risk_value: bool,
) -> None:
    stages = _positive_stages()
    stages["D-5"][risk_field] = risk_value

    result = score_early_observation(stages)

    contraction = _component(result.components, "selling_pressure_contraction")
    compression = _component(result.components, "tight_body_compression")
    lower_shadow = _component(result.components, "bullish_lower_shadow_support")
    assert contraction.passed is False
    assert contraction.reason == "no_demand_risk"
    assert compression.passed is False
    assert compression.reason == "no_demand_risk"
    assert lower_shadow.passed is False
    assert lower_shadow.reason == "lower_shadow_risk"
    assert result.eligibility == "NOT_ELIGIBLE"


def test_small_body_alone_does_not_create_watch_eligibility() -> None:
    stages = _positive_stages()
    stages["D-5"]["volume_ratio_20"] = 1.0
    stages["D-5"]["volume_ratio_slope"] = 0.0

    result = score_early_observation(stages)

    assert _component(result.components, "tight_body_compression").passed is False
    assert result.eligibility == "NOT_ELIGIBLE"


def test_falling_but_still_high_volume_ratio_is_not_low_volume_context() -> None:
    stages = _positive_stages()
    stages["D-5"]["volume_ratio_20"] = 1.20
    stages["D-5"]["volume_ratio_slope"] = -0.20

    result = score_early_observation(stages)

    contraction = _component(result.components, "selling_pressure_contraction")
    assert contraction.passed is False
    assert contraction.reason == "selling_pressure_not_contracting"
    assert result.eligibility == "NOT_ELIGIBLE"


def test_valid_lower_shadow_support_is_only_unstable_context_bonus() -> None:
    result = score_early_observation(_positive_stages())

    lower_shadow = _component(result.components, "bullish_lower_shadow_support")
    assert lower_shadow.passed is True
    assert lower_shadow.points == 5.0
    assert lower_shadow.reason == "bullish_lower_shadow_support"
    assert lower_shadow.evidence_status == "unstable_context_only"


@pytest.mark.parametrize(
    "d5_mutation",
    [
        {"close_location_in_bar": 0.30},
        {"volume_ratio_20": 1.60, "volume_ratio_slope": -0.1},
        {"long_upper_shadow": True},
    ],
)
def test_lower_shadow_with_weak_close_volume_kill_or_upper_supply_gets_no_bonus(
    d5_mutation: dict[str, float | bool],
) -> None:
    stages = _positive_stages()
    stages["D-5"].update(d5_mutation)

    result = score_early_observation(stages)

    lower_shadow = _component(result.components, "bullish_lower_shadow_support")
    assert lower_shadow.passed is False
    assert lower_shadow.points == 0.0
    assert lower_shadow.reason == "lower_shadow_risk"


def test_optional_body_and_lower_shadow_are_not_eligibility_requirements() -> None:
    stages = _positive_stages()
    for feature in (
        "pre5_min_abs_open_close_pct",
        "lower_shadow_body_ratio",
        "lower_shadow_pct",
        "close_location_in_bar",
    ):
        stages["D-5"].pop(feature)

    result = score_early_observation(stages)

    compression = _component(result.components, "tight_body_compression")
    lower_shadow = _component(result.components, "bullish_lower_shadow_support")
    assert result.score == 90.0
    assert result.missing_features == ()
    assert result.eligibility == "SHADOW_WATCH_ELIGIBLE"
    assert compression.passed is None
    assert compression.reason == "compression_unconfirmed"
    assert lower_shadow.passed is None
    assert lower_shadow.reason == "lower_shadow_unconfirmed"


def test_missing_core_volume_is_not_zero_filled() -> None:
    stages = _positive_stages()
    stages["D-5"].pop("volume_ratio_20")
    stages["D-5"].pop("volume_ratio_slope")

    result = score_early_observation(stages)

    assert result.score is None
    assert result.early_score is None
    assert result.eligibility == "INSUFFICIENT_FEATURES"
    assert "D-5.volume_ratio_20_or_slope" in result.missing_features
    assert _component(result.components, "selling_pressure_contraction").passed is None


def test_confirmation_change_does_not_change_early_score_or_watch_eligibility() -> None:
    confirmed_stages = _positive_stages()
    rejected_stages = _positive_stages()
    rejected_stages["D"]["pressure_breakout"] = False

    confirmed = score_early_observation(confirmed_stages)
    rejected = score_early_observation(rejected_stages)

    assert confirmed.early_score == rejected.early_score == 100.0
    assert confirmed.eligibility == rejected.eligibility == "SHADOW_WATCH_ELIGIBLE"
    assert confirmed.confirmation_status == "CONFIRMED"
    assert rejected.confirmation_status == "NOT_CONFIRMED"
    assert rejected.confirmation_score == 0.0


def test_future_or_evaluator_fields_are_rejected() -> None:
    stages = _positive_stages()
    stages["D-3"]["d5_adjusted_return_pct"] = 25.0

    with pytest.raises(ValueError, match="future/evaluator fields"):
        score_early_observation(stages)


def test_dataframe_rows_and_mapping_have_identical_results() -> None:
    stages = _positive_stages()
    rows = pd.DataFrame([{"relative_day": stage, **row} for stage, row in stages.items()])

    mapping_result = score_early_observation(stages)
    frame_result = score_early_observation(rows)

    assert frame_result.to_dict() == mapping_result.to_dict()


def test_zero_ma20_slope_is_not_positive() -> None:
    stages = _positive_stages()
    stages["D-5"]["ma20_slope_pct"] = 0.0

    result = score_early_observation(stages)

    assert _component(result.components, "ma20_positive_trend").passed is False
    assert _component(result.components, "selling_pressure_contraction").reason == (
        "no_demand_risk"
    )
    assert result.eligibility == "NOT_ELIGIBLE"


def test_config_rejects_weights_that_do_not_sum_to_100() -> None:
    with pytest.raises(ValueError, match="sum to 100"):
        EarlyObservationScoreConfig(weight_k_turn_up=9.0)


def _component(
    components: tuple[EarlyObservationComponent, ...],
    name: str,
) -> EarlyObservationComponent:
    return next(component for component in components if component.name == name)


def _positive_stages() -> dict[str, dict[str, float | bool | list[float]]]:
    return {
        "D-5": {
            "volume_ratio_20": 0.50,
            "volume_ratio_slope": -0.05,
            "ma20_slope_pct": 0.20,
            "daily_return_pct": -0.40,
            "long_upper_shadow": False,
            "persistent_price_decline": False,
            "pre5_min_abs_open_close_pct": 1.20,
            "lower_shadow_body_ratio": 2.0,
            "lower_shadow_pct": 0.9,
            "close_location_in_bar": 0.75,
            "volume_spike_selloff": False,
        },
        "D-3": {
            "daily_return_pct": 0.10,
            "kd_k_change_1d": 0.20,
            "volume_slope_acceleration": 0.10,
            "volume_ratio_20": 0.60,
        },
        "D-1": {
            "close_to_ma20_pct": 0.0,
            "daily_return_pct": 0.50,
            "volume_ratio_20": 0.80,
        },
        "D": {"pressure_breakout": True},
    }
