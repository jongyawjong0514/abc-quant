"""Interpretable D-5 through D shadow-only early observation score."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

import pandas as pd


STAGE_ORDER = ("D-5", "D-3", "D-1", "D")
_STAGE_LABELS = {
    "D-5": "D5_SETUP",
    "D-3": "D3_EARLY_TURN",
    "D-1": "D1_EARLY_OBSERVATION",
    "D": "D_CONFIRMATION_REVIEW",
}
_STAGE_ALIASES = {
    "D-5": "D-5",
    "D5": "D-5",
    "T-5": "D-5",
    "T5": "D-5",
    "D-3": "D-3",
    "D3": "D-3",
    "T-3": "D-3",
    "T3": "D-3",
    "D-1": "D-1",
    "D1": "D-1",
    "T-1": "D-1",
    "T1": "D-1",
    "D": "D",
    "T": "D",
    "SIGNAL": "D",
}
_FUTURE_EXACT_FIELDS = {
    "d5_adjusted_return_pct",
    "d5_group",
    "d5_close_date",
    "target_gain_ge10",
    "target_gain_ge20",
    "target_loss",
}
_FUTURE_PREFIXES = ("future_", "forward_", "target_", "evaluator_")


@dataclass(frozen=True)
class EarlyObservationScoreConfig:
    """All thresholds and weights for the shadow observation score."""

    max_volume_ratio_20: float = 0.50
    max_volume_ratio_slope: float = 0.0
    min_ma20_slope_pct: float = 0.0
    min_pullback_return_pct: float = -4.0
    max_pullback_return_pct: float = 0.5
    max_tight_body_pct: float = 1.2
    max_upper_shadow_body_ratio: float = 1.0
    max_upper_tail_count: int = 0
    max_consecutive_down_days: int = 2
    min_price_stabilization_return_pct: float = 0.0
    min_k_change_1d: float = 0.0
    min_volume_slope_acceleration: float = 0.0
    min_close_to_ma20_pct: float = 0.0
    min_price_strengthening_pct: float = 0.0
    min_volume_ratio_increase: float = 0.0
    min_pressure_breakout_pct: float = 0.0
    min_lower_shadow_body_ratio: float = 1.5
    min_lower_shadow_pct: float = 0.8
    min_close_location_in_bar: float = 0.60
    max_lower_shadow_volume_ratio: float = 1.50
    weight_ma20_positive: float = 10.0
    weight_selling_pressure_contraction: float = 25.0
    weight_tight_body_compression: float = 5.0
    weight_bullish_lower_shadow_support: float = 5.0
    weight_price_stabilization: float = 10.0
    weight_k_turn_up: float = 10.0
    weight_volume_slope_acceleration: float = 10.0
    weight_reclaim_ma20: float = 10.0
    weight_price_volume_strengthening: float = 15.0

    def __post_init__(self) -> None:
        weights = self.early_weights
        if any(weight < 0 for weight in weights):
            raise ValueError("early observation weights must be non-negative")
        if abs(sum(weights) - 100.0) > 1e-9:
            raise ValueError("early observation weights must sum to 100")
        if self.max_tight_body_pct < 0:
            raise ValueError("max_tight_body_pct must be non-negative")
        if not 0.0 <= self.min_close_location_in_bar <= 1.0:
            raise ValueError("min_close_location_in_bar must be between 0 and 1")
        if self.min_pullback_return_pct > self.max_pullback_return_pct:
            raise ValueError("pullback return bounds are reversed")

    @property
    def early_weights(self) -> tuple[float, ...]:
        return (
            self.weight_ma20_positive,
            self.weight_selling_pressure_contraction,
            self.weight_tight_body_compression,
            self.weight_bullish_lower_shadow_support,
            self.weight_price_stabilization,
            self.weight_k_turn_up,
            self.weight_volume_slope_acceleration,
            self.weight_reclaim_ma20,
            self.weight_price_volume_strengthening,
        )


@dataclass(frozen=True)
class EarlyObservationComponent:
    """One auditable contribution to the early or confirmation view."""

    name: str
    stage: str
    passed: bool | None
    points: float
    max_points: float
    reason: str
    evidence_status: str
    used_features: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EarlyObservationScoreResult:
    """Shadow score result; confirmation never contributes to the early score."""

    stage: str
    score: float | None
    early_score: float | None
    confirmation_score: float | None
    confirmation_status: str
    confirmed: bool | None
    components: tuple[EarlyObservationComponent, ...]
    missing_features: tuple[str, ...]
    eligibility: str
    mode: str = "shadow_observation_only"
    formal_trade_effect: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "score": self.score,
            "early_score": self.early_score,
            "confirmation_score": self.confirmation_score,
            "confirmation_status": self.confirmation_status,
            "confirmed": self.confirmed,
            "components": [component.to_dict() for component in self.components],
            "missing_features": list(self.missing_features),
            "eligibility": self.eligibility,
            "mode": self.mode,
            "formal_trade_effect": self.formal_trade_effect,
        }


def score_early_observation(
    stages: Mapping[str, Any] | pd.DataFrame | pd.Series,
    *,
    config: EarlyObservationScoreConfig | None = None,
) -> EarlyObservationScoreResult:
    """Score causal D-5/D-3/D-1 evidence and evaluate D confirmation separately."""
    rules = config or EarlyObservationScoreConfig()
    rows = _normalize_stage_rows(stages)
    _reject_future_fields(rows)
    if not rows:
        return EarlyObservationScoreResult(
            stage="INSUFFICIENT_FEATURES",
            score=None,
            early_score=None,
            confirmation_score=None,
            confirmation_status="NOT_EVALUATED",
            confirmed=None,
            components=tuple(_pending_components(rules)),
            missing_features=("D-5.__stage__",),
            eligibility="INSUFFICIENT_FEATURES",
        )

    furthest_index = max(STAGE_ORDER.index(stage) for stage in rows)
    furthest_stage = STAGE_ORDER[furthest_index]
    required_stages = STAGE_ORDER[: furthest_index + 1]
    chronology_missing = [f"{stage}.__stage__" for stage in required_stages if stage not in rows]

    components: list[EarlyObservationComponent] = []
    missing: list[str] = chronology_missing.copy()
    d5_context: dict[str, Any] | None = None

    if "D-5" in rows:
        d5_components, d5_missing, d5_context = _score_d5(rows["D-5"], rules)
        components.extend(d5_components)
        missing.extend(d5_missing)
    else:
        components.extend(_pending_d5_components(rules))

    if "D-3" in rows:
        d3_components, d3_missing = _score_d3(rows["D-3"], rules)
        components.extend(d3_components)
        missing.extend(d3_missing)
    else:
        components.extend(_pending_d3_components(rules))

    if "D-1" in rows:
        d1_components, d1_missing = _score_d1(
            rows["D-1"], rows.get("D-3"), rules
        )
        components.extend(d1_components)
        missing.extend(d1_missing)
    else:
        components.extend(_pending_d1_components(rules))

    confirmation_component, confirmation_missing = _score_confirmation(rows.get("D"), rules)
    components.append(confirmation_component)
    missing.extend(confirmation_missing)
    missing_features = tuple(dict.fromkeys(missing))
    early_missing = any(not item.startswith("D.") for item in missing_features)

    early_score = None
    if not early_missing:
        early_score = round(
            min(100.0, sum(component.points for component in components[:-1])), 6
        )

    confirmation_status = "NOT_EVALUATED"
    confirmation_score: float | None = None
    confirmed: bool | None = None
    if "D" in rows:
        if confirmation_missing:
            confirmation_status = "INSUFFICIENT_FEATURES"
        else:
            confirmed = bool(confirmation_component.passed)
            confirmation_score = 100.0 if confirmed else 0.0
            confirmation_status = "CONFIRMED" if confirmed else "NOT_CONFIRMED"

    d5_core_pass = bool(d5_context and d5_context["core_watch_context"])
    if missing_features:
        eligibility = "INSUFFICIENT_FEATURES"
    elif d5_core_pass:
        eligibility = "SHADOW_WATCH_ELIGIBLE"
    else:
        eligibility = "NOT_ELIGIBLE"

    return EarlyObservationScoreResult(
        stage=_STAGE_LABELS[furthest_stage],
        score=early_score,
        early_score=early_score,
        confirmation_score=confirmation_score,
        confirmation_status=confirmation_status,
        confirmed=confirmed,
        components=tuple(components),
        missing_features=missing_features,
        eligibility=eligibility,
    )


def _score_d5(
    row: Mapping[str, Any], config: EarlyObservationScoreConfig
) -> tuple[list[EarlyObservationComponent], list[str], dict[str, Any]]:
    missing: list[str] = []
    ma20_slope, ma20_feature = _first_number(
        row, ("ma20_slope_pct", "sma20_slope_5d_pct", "ma20_slope")
    )
    volume_ratio, volume_ratio_feature = _first_number(
        row, ("volume_ratio_20", "day_volume_ratio_20")
    )
    volume_slope, volume_slope_feature = _first_number(
        row,
        (
            "volume_ratio_slope",
            "volume_ratio_20_slope",
            "volume_slope_5d_pct",
            "volume_slope_5d_pctpt",
        ),
    )
    daily_return, return_feature = _first_number(
        row, ("daily_return_pct", "pullback_return_pct")
    )
    upper_risk, upper_feature = _upper_shadow_risk(row, config)
    decline_risk, decline_feature = _persistent_decline_risk(row, config)

    if ma20_slope is None:
        missing.append("D-5.ma20_slope")
    if volume_ratio is None and volume_slope is None:
        missing.append("D-5.volume_ratio_20_or_slope")
    if daily_return is None:
        missing.append("D-5.daily_return_pct")
    if upper_risk is None:
        missing.append("D-5.upper_shadow_guard")
    if decline_risk is None:
        missing.append("D-5.persistent_decline_guard")

    ma20_positive = ma20_slope is not None and ma20_slope > config.min_ma20_slope_pct
    contraction = bool(
        volume_ratio <= config.max_volume_ratio_20
        if volume_ratio is not None
        else volume_slope is not None
        and volume_slope < config.max_volume_ratio_slope
    )
    pullback = bool(
        daily_return is not None
        and config.min_pullback_return_pct <= daily_return <= config.max_pullback_return_pct
    )
    guard_safe = upper_risk is False and decline_risk is False
    core_watch_context = contraction and pullback and ma20_positive and guard_safe

    ma20_component = _component(
        name="ma20_positive_trend",
        stage="D-5",
        passed=ma20_positive if ma20_slope is not None else None,
        max_points=config.weight_ma20_positive,
        pass_reason="ma20_slope_positive",
        fail_reason="ma20_slope_not_positive",
        evidence_status="core",
        used_features=(ma20_feature,),
    )
    if any(value is None for value in (daily_return, upper_risk, decline_risk)) or (
        volume_ratio is None and volume_slope is None
    ):
        contraction_passed: bool | None = None
        contraction_reason = "selling_pressure_context_missing"
    elif core_watch_context:
        contraction_passed = True
        contraction_reason = "low_volume_bullish_context"
    elif contraction and (not ma20_positive or not guard_safe or not pullback):
        contraction_passed = False
        contraction_reason = "no_demand_risk"
    else:
        contraction_passed = False
        contraction_reason = "selling_pressure_not_contracting"
    contraction_component = _component(
        name="selling_pressure_contraction",
        stage="D-5",
        passed=contraction_passed,
        max_points=config.weight_selling_pressure_contraction,
        pass_reason=contraction_reason,
        fail_reason=contraction_reason,
        evidence_status="core",
        used_features=(
            volume_ratio_feature,
            volume_slope_feature,
            return_feature,
            ma20_feature,
            upper_feature,
            decline_feature,
        ),
    )

    tight_body, body_features = _tight_body_evidence(row)
    if tight_body is None:
        compression_passed: bool | None = None
        compression_reason = "compression_unconfirmed"
    elif tight_body <= config.max_tight_body_pct and core_watch_context:
        compression_passed = True
        compression_reason = "compression_in_bullish_context"
    elif tight_body <= config.max_tight_body_pct and not core_watch_context:
        compression_passed = False
        compression_reason = "no_demand_risk"
    else:
        compression_passed = False
        compression_reason = "compression_threshold_not_met"
    compression_component = _component(
        name="tight_body_compression",
        stage="D-5",
        passed=compression_passed,
        max_points=config.weight_tight_body_compression,
        pass_reason=compression_reason,
        fail_reason=compression_reason,
        evidence_status="unstable_context_only",
        used_features=body_features,
    )

    lower_component = _score_lower_shadow_support(
        row,
        config,
        ma20_positive=ma20_positive,
        upper_risk=upper_risk,
        decline_risk=decline_risk,
        volume_ratio=volume_ratio,
    )
    context = {
        "ma20_positive": ma20_positive,
        "contraction": contraction,
        "pullback": pullback,
        "guard_safe": guard_safe,
        "core_watch_context": core_watch_context,
    }
    return (
        [ma20_component, contraction_component, compression_component, lower_component],
        missing,
        context,
    )


def _score_lower_shadow_support(
    row: Mapping[str, Any],
    config: EarlyObservationScoreConfig,
    *,
    ma20_positive: bool,
    upper_risk: bool | None,
    decline_risk: bool | None,
    volume_ratio: float | None,
) -> EarlyObservationComponent:
    lower_ratio, lower_ratio_feature = _first_number(
        row, ("lower_shadow_body_ratio", "lower_wick_body_ratio")
    )
    lower_pct, lower_pct_feature = _first_number(
        row, ("lower_shadow_pct", "lower_wick_pct")
    )
    close_location, close_feature = _first_number(
        row, ("close_location_in_bar", "bar_close_location")
    )
    spike_flag, spike_feature = _first_bool(
        row, ("volume_spike_selloff", "explosive_volume_selloff")
    )
    daily_return, _ = _first_number(row, ("daily_return_pct", "pullback_return_pct"))
    shape_available = lower_ratio is not None or lower_pct is not None
    shape_pass = bool(
        (lower_ratio is not None and lower_ratio >= config.min_lower_shadow_body_ratio)
        or (lower_pct is not None and lower_pct >= config.min_lower_shadow_pct)
    )
    close_strong = bool(
        close_location is not None
        and close_location >= config.min_close_location_in_bar
    )
    volume_kill = bool(
        spike_flag is True
        or (
            volume_ratio is not None
            and volume_ratio > config.max_lower_shadow_volume_ratio
            and daily_return is not None
            and daily_return < 0.0
        )
    )
    risk = bool(
        upper_risk is True
        or decline_risk is True
        or volume_kill
        or (close_location is not None and not close_strong)
    )
    if not shape_available or close_location is None or upper_risk is None or decline_risk is None:
        passed: bool | None = None
        reason = "lower_shadow_unconfirmed"
    elif risk:
        passed = False
        reason = "lower_shadow_risk"
    elif shape_pass and close_strong and ma20_positive:
        passed = True
        reason = "bullish_lower_shadow_support"
    else:
        passed = False
        reason = "lower_shadow_unconfirmed"
    return _component(
        name="bullish_lower_shadow_support",
        stage="D-5",
        passed=passed,
        max_points=config.weight_bullish_lower_shadow_support,
        pass_reason=reason,
        fail_reason=reason,
        evidence_status="unstable_context_only",
        used_features=(
            lower_ratio_feature,
            lower_pct_feature,
            close_feature,
            spike_feature,
        ),
    )


def _score_d3(
    row: Mapping[str, Any], config: EarlyObservationScoreConfig
) -> tuple[list[EarlyObservationComponent], list[str]]:
    missing: list[str] = []
    explicit_stable, stable_feature = _first_bool(
        row, ("price_stabilized", "price_stabilization")
    )
    daily_return, return_feature = _first_number(row, ("daily_return_pct",))
    if explicit_stable is None and daily_return is None:
        missing.append("D-3.price_stabilization")
        stabilized: bool | None = None
    else:
        stabilized = explicit_stable if explicit_stable is not None else bool(
            daily_return is not None
            and daily_return >= config.min_price_stabilization_return_pct
        )
    k_change, k_feature = _first_number(
        row, ("kd_k_change_1d", "k_change_1d", "k_slope")
    )
    if k_change is None:
        missing.append("D-3.k_change_1d")
    volume_acceleration, acceleration_feature = _first_number(
        row,
        (
            "volume_slope_acceleration",
            "volume_slope_accel_5_pctpt",
            "volume_slope_accel_5",
            "volume_slope_accel_3_pctpt",
            "volume_slope_accel_3",
        ),
    )
    if volume_acceleration is None:
        missing.append("D-3.volume_slope_acceleration")
    return (
        [
            _component(
                name="price_stabilization",
                stage="D-3",
                passed=stabilized,
                max_points=config.weight_price_stabilization,
                pass_reason="price_stabilized",
                fail_reason="price_not_stabilized",
                evidence_status="core",
                used_features=(stable_feature, return_feature),
            ),
            _component(
                name="k_turn_up",
                stage="D-3",
                passed=(
                    k_change > config.min_k_change_1d if k_change is not None else None
                ),
                max_points=config.weight_k_turn_up,
                pass_reason="k_turn_up",
                fail_reason="k_not_turning_up",
                evidence_status="core",
                used_features=(k_feature,),
            ),
            _component(
                name="volume_slope_acceleration",
                stage="D-3",
                passed=(
                    volume_acceleration > config.min_volume_slope_acceleration
                    if volume_acceleration is not None
                    else None
                ),
                max_points=config.weight_volume_slope_acceleration,
                pass_reason="volume_slope_acceleration_positive",
                fail_reason="volume_slope_acceleration_not_positive",
                evidence_status="core",
                used_features=(acceleration_feature,),
            ),
        ],
        missing,
    )


def _score_d1(
    row: Mapping[str, Any],
    d3_row: Mapping[str, Any] | None,
    config: EarlyObservationScoreConfig,
) -> tuple[list[EarlyObservationComponent], list[str]]:
    missing: list[str] = []
    explicit_reclaim, reclaim_feature = _first_bool(row, ("reclaimed_ma20",))
    close_to_ma20, close_feature = _first_number(
        row, ("close_to_ma20_pct", "close_to_sma20_pct")
    )
    if explicit_reclaim is None and close_to_ma20 is None:
        missing.append("D-1.reclaim_ma20")
        reclaimed: bool | None = None
    else:
        reclaimed = explicit_reclaim if explicit_reclaim is not None else bool(
            close_to_ma20 is not None
            and close_to_ma20 >= config.min_close_to_ma20_pct
        )

    explicit_strength, strength_feature = _first_bool(
        row, ("price_volume_strengthening",)
    )
    daily_return, return_feature = _first_number(row, ("daily_return_pct",))
    volume_change, volume_change_feature = _first_number(
        row, ("volume_ratio_change_1d", "volume_ratio_20_change_1d")
    )
    if volume_change is None and d3_row is not None:
        d1_volume, d1_volume_feature = _first_number(
            row, ("volume_ratio_20", "day_volume_ratio_20")
        )
        d3_volume, d3_volume_feature = _first_number(
            d3_row, ("volume_ratio_20", "day_volume_ratio_20")
        )
        if d1_volume is not None and d3_volume is not None:
            volume_change = d1_volume - d3_volume
            volume_change_feature = f"{d1_volume_feature}-{d3_volume_feature}"
    if explicit_strength is None and daily_return is None:
        missing.append("D-1.price_strengthening")
    if explicit_strength is None and volume_change is None:
        missing.append("D-1.volume_strengthening")
    if explicit_strength is not None:
        strengthening: bool | None = explicit_strength
    elif daily_return is None or volume_change is None:
        strengthening = None
    else:
        strengthening = bool(
            daily_return > config.min_price_strengthening_pct
            and volume_change > config.min_volume_ratio_increase
        )
    return (
        [
            _component(
                name="reclaim_ma20",
                stage="D-1",
                passed=reclaimed,
                max_points=config.weight_reclaim_ma20,
                pass_reason="reclaimed_ma20",
                fail_reason="ma20_not_reclaimed",
                evidence_status="core",
                used_features=(reclaim_feature, close_feature),
            ),
            _component(
                name="price_volume_strengthening",
                stage="D-1",
                passed=strengthening,
                max_points=config.weight_price_volume_strengthening,
                pass_reason="price_volume_strengthening",
                fail_reason="price_volume_not_strengthening",
                evidence_status="core",
                used_features=(strength_feature, return_feature, volume_change_feature),
            ),
        ],
        missing,
    )


def _score_confirmation(
    row: Mapping[str, Any] | None, config: EarlyObservationScoreConfig
) -> tuple[EarlyObservationComponent, list[str]]:
    if row is None:
        return (
            EarlyObservationComponent(
                name="pressure_breakout_confirmation",
                stage="D",
                passed=None,
                points=0.0,
                max_points=0.0,
                reason="stage_not_observed",
                evidence_status="confirmation_only",
            ),
            [],
        )
    explicit_breakout, breakout_feature = _first_bool(
        row, ("pressure_breakout", "confirmed_pressure_breakout")
    )
    distance, distance_feature = _first_number(
        row, ("close_to_pressure_pct", "pressure_breakout_pct")
    )
    if explicit_breakout is None and distance is None:
        passed: bool | None = None
        missing = ["D.pressure_breakout"]
    else:
        passed = explicit_breakout if explicit_breakout is not None else bool(
            distance is not None and distance >= config.min_pressure_breakout_pct
        )
        missing = []
    reason = (
        "pressure_breakout_confirmed"
        if passed is True
        else "pressure_breakout_not_confirmed"
        if passed is False
        else "pressure_breakout_missing"
    )
    return (
        EarlyObservationComponent(
            name="pressure_breakout_confirmation",
            stage="D",
            passed=passed,
            points=0.0,
            max_points=0.0,
            reason=reason,
            evidence_status="confirmation_only",
            used_features=_clean_features((breakout_feature, distance_feature)),
        ),
        missing,
    )


def _pending_components(
    config: EarlyObservationScoreConfig,
) -> list[EarlyObservationComponent]:
    return [
        *_pending_d5_components(config),
        *_pending_d3_components(config),
        *_pending_d1_components(config),
        _score_confirmation(None, config)[0],
    ]


def _pending_d5_components(
    config: EarlyObservationScoreConfig,
) -> list[EarlyObservationComponent]:
    return [
        _pending_component("ma20_positive_trend", "D-5", config.weight_ma20_positive, "core"),
        _pending_component(
            "selling_pressure_contraction",
            "D-5",
            config.weight_selling_pressure_contraction,
            "core",
        ),
        _pending_component(
            "tight_body_compression",
            "D-5",
            config.weight_tight_body_compression,
            "unstable_context_only",
        ),
        _pending_component(
            "bullish_lower_shadow_support",
            "D-5",
            config.weight_bullish_lower_shadow_support,
            "unstable_context_only",
        ),
    ]


def _pending_d3_components(
    config: EarlyObservationScoreConfig,
) -> list[EarlyObservationComponent]:
    return [
        _pending_component(
            "price_stabilization", "D-3", config.weight_price_stabilization, "core"
        ),
        _pending_component("k_turn_up", "D-3", config.weight_k_turn_up, "core"),
        _pending_component(
            "volume_slope_acceleration",
            "D-3",
            config.weight_volume_slope_acceleration,
            "core",
        ),
    ]


def _pending_d1_components(
    config: EarlyObservationScoreConfig,
) -> list[EarlyObservationComponent]:
    return [
        _pending_component("reclaim_ma20", "D-1", config.weight_reclaim_ma20, "core"),
        _pending_component(
            "price_volume_strengthening",
            "D-1",
            config.weight_price_volume_strengthening,
            "core",
        ),
    ]


def _pending_component(
    name: str, stage: str, max_points: float, evidence_status: str
) -> EarlyObservationComponent:
    return EarlyObservationComponent(
        name=name,
        stage=stage,
        passed=None,
        points=0.0,
        max_points=max_points,
        reason="stage_not_observed",
        evidence_status=evidence_status,
    )


def _component(
    *,
    name: str,
    stage: str,
    passed: bool | None,
    max_points: float,
    pass_reason: str,
    fail_reason: str,
    evidence_status: str,
    used_features: Sequence[str | None],
) -> EarlyObservationComponent:
    return EarlyObservationComponent(
        name=name,
        stage=stage,
        passed=passed,
        points=max_points if passed is True else 0.0,
        max_points=max_points,
        reason=pass_reason if passed is True else fail_reason,
        evidence_status=evidence_status,
        used_features=_clean_features(used_features),
    )


def _normalize_stage_rows(
    stages: Mapping[str, Any] | pd.DataFrame | pd.Series,
) -> dict[str, dict[str, Any]]:
    if isinstance(stages, pd.Series):
        stages = stages.to_dict()
    if isinstance(stages, pd.DataFrame):
        stage_column = "relative_day" if "relative_day" in stages else "stage" if "stage" in stages else None
        if stage_column is None:
            raise ValueError("DataFrame input requires relative_day or stage")
        normalized: dict[str, dict[str, Any]] = {}
        for _, row in stages.iterrows():
            stage = _normalize_stage(row[stage_column])
            if stage in normalized:
                raise ValueError(f"duplicate observation stage: {stage}")
            normalized[stage] = row.drop(labels=[stage_column]).to_dict()
        return normalized
    if not isinstance(stages, Mapping):
        raise TypeError("stages must be a mapping, Series, or DataFrame")
    if "relative_day" in stages or "stage" in stages:
        stage_key = "relative_day" if "relative_day" in stages else "stage"
        stage = _normalize_stage(stages[stage_key])
        return {stage: {key: value for key, value in stages.items() if key != stage_key}}
    normalized = {}
    for raw_stage, raw_row in stages.items():
        stage = _normalize_stage(raw_stage)
        if isinstance(raw_row, pd.Series):
            raw_row = raw_row.to_dict()
        if not isinstance(raw_row, Mapping):
            raise TypeError(f"{stage} observation must be a mapping or Series")
        if stage in normalized:
            raise ValueError(f"duplicate observation stage: {stage}")
        normalized[stage] = dict(raw_row)
    return normalized


def _normalize_stage(value: Any) -> str:
    key = str(value).strip().upper().replace("_", "-")
    if key not in _STAGE_ALIASES:
        raise ValueError(f"unsupported observation stage: {value}")
    return _STAGE_ALIASES[key]


def _reject_future_fields(rows: Mapping[str, Mapping[str, Any]]) -> None:
    forbidden: list[str] = []
    for stage, row in rows.items():
        for field in row:
            normalized = str(field).strip().lower()
            if normalized in _FUTURE_EXACT_FIELDS or normalized.startswith(_FUTURE_PREFIXES):
                forbidden.append(f"{stage}.{field}")
    if forbidden:
        raise ValueError(f"future/evaluator fields are not allowed: {sorted(forbidden)}")


def _upper_shadow_risk(
    row: Mapping[str, Any], config: EarlyObservationScoreConfig
) -> tuple[bool | None, str | None]:
    explicit, feature = _first_bool(row, ("long_upper_shadow", "has_long_upper_shadow"))
    if explicit is not None:
        return explicit, feature
    ratio, feature = _first_number(
        row, ("upper_shadow_body_ratio", "upper_wick_body_ratio")
    )
    if ratio is not None:
        return ratio > config.max_upper_shadow_body_ratio, feature
    count, feature = _first_number(row, ("pre5_upper_tail_count", "upper_tail_count"))
    if count is not None:
        return count > config.max_upper_tail_count, feature
    return None, None


def _persistent_decline_risk(
    row: Mapping[str, Any], config: EarlyObservationScoreConfig
) -> tuple[bool | None, str | None]:
    explicit, feature = _first_bool(
        row,
        (
            "persistent_price_decline",
            "persistent_new_lows",
            "continuing_breakdown",
        ),
    )
    if explicit is not None:
        return explicit, feature
    count, feature = _first_number(
        row, ("consecutive_down_days", "consecutive_new_low_days")
    )
    if count is not None:
        return count > config.max_consecutive_down_days, feature
    return None, None


def _tight_body_evidence(row: Mapping[str, Any]) -> tuple[float | None, tuple[str, ...]]:
    value, feature = _first_number(
        row, ("pre5_min_abs_open_close_pct", "pre5_min_body_pct")
    )
    if value is not None:
        return value, _clean_features((feature,))
    values, feature = _first_sequence(
        row, ("pre5_abs_open_close_pct", "pre5_body_pct_values")
    )
    numeric_values = [_number(item) for item in values] if values is not None else []
    valid_values = [item for item in numeric_values if item is not None]
    if valid_values:
        return min(valid_values), _clean_features((feature,))
    opens, open_feature = _first_sequence(row, ("pre5_open", "pre5_open_values"))
    closes, close_feature = _first_sequence(row, ("pre5_close", "pre5_close_values"))
    if opens is None or closes is None or len(opens) != len(closes) or not opens:
        return None, ()
    body_values: list[float] = []
    for open_value, close_value in zip(opens, closes, strict=True):
        open_number = _number(open_value)
        close_number = _number(close_value)
        if open_number is None or close_number is None or open_number == 0.0:
            continue
        body_values.append(abs(close_number - open_number) / abs(open_number) * 100.0)
    if not body_values:
        return None, ()
    return min(body_values), _clean_features((open_feature, close_feature))


def _first_number(
    row: Mapping[str, Any], aliases: Sequence[str]
) -> tuple[float | None, str | None]:
    for alias in aliases:
        if alias in row:
            number = _number(row[alias])
            if number is not None:
                return number, alias
    return None, None


def _first_bool(
    row: Mapping[str, Any], aliases: Sequence[str]
) -> tuple[bool | None, str | None]:
    for alias in aliases:
        if alias in row:
            boolean = _boolean(row[alias])
            if boolean is not None:
                return boolean, alias
    return None, None


def _first_sequence(
    row: Mapping[str, Any], aliases: Sequence[str]
) -> tuple[list[Any] | None, str | None]:
    for alias in aliases:
        if alias not in row:
            continue
        value = row[alias]
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return list(value), alias
        if isinstance(value, (pd.Index, pd.Series)):
            return value.tolist(), alias
    return None, None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _boolean(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
        return None
    if value in (0, 1):
        return bool(value)
    return None


def _clean_features(features: Sequence[str | None]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(feature for feature in features if feature))
