import numpy as np
import pandas as pd

from abc_quant.validation.pit_grouping import (
    ALLOWED_MARKET_REGIMES,
    INSUFFICIENT_DATA,
    INSUFFICIENT_FEATURES,
    asof_join_point_in_time,
    attach_concept_membership,
    beta_binomial_partial_pool,
    build_pit_groupings,
)


def _observations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2026-01-10"] * 4,
            "stock_id": ["1101", "1102", "2201", "2202"],
            "score": [10.0, 20.0, 30.0, 40.0],
            "free_float_market_cap": [100.0, 200.0, 300.0, 400.0],
            "avg_turnover_20_twd": [10.0, 20.0, 30.0, 40.0],
            "market_trend": ["up", "flat", "down", "trend_up"],
            "market_volatility": ["low", "high", "low", "volatility_high"],
        }
    )


def _sector_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stock_id": ["1101", "1102", "2201", "2202"],
            "sector": ["CEMENT", "CEMENT", "AUTO", "AUTO"],
            "effective_date": ["2026-01-01"] * 4,
            "available_date": ["2026-01-02"] * 4,
        }
    )


def test_future_sector_row_is_not_selected_by_asof_join() -> None:
    observations = pd.DataFrame(
        {
            "observation_date": ["2026-01-10", "2026-01-10"],
            "stock_id": ["2330", "2317"],
        }
    )
    future = pd.DataFrame(
        {
            "stock_id": ["2330", "2317"],
            "sector": ["SEMICONDUCTOR", "ELECTRONICS"],
            "effective_date": ["2026-01-01", "2026-01-11"],
            "available_date": ["2026-01-12", "2026-01-01"],
        }
    )

    joined = asof_join_point_in_time(
        observations,
        future,
        feature_columns=["sector"],
        available_date_column="available_date",
        prefix="sector",
    )

    assert joined["sector"].isna().all()
    assert joined["sector_pit_status"].eq(INSUFFICIENT_DATA).all()
    assert joined["sector_source_date"].isna().all()


def test_same_day_market_and_sector_percentiles_are_cross_sectional() -> None:
    grouped = build_pit_groupings(
        _observations(),
        sector_history=_sector_history(),
    )

    assert grouped["market_percentile"].tolist() == [0.25, 0.5, 0.75, 1.0]
    assert grouped["sector_within_percentile"].tolist() == [0.5, 1.0, 0.5, 1.0]
    assert grouped["sector"].tolist() == ["CEMENT", "CEMENT", "AUTO", "AUTO"]
    assert grouped["size_tier"].tolist() == ["small", "mid", "large", "large"]
    assert grouped["liquidity_tier"].tolist() == ["low", "mid", "high", "high"]
    assert set(grouped["market_regime"]).issubset(ALLOWED_MARKET_REGIMES)
    assert not grouped["formal_trade_effect"].any()


def test_size_uses_free_float_market_cap_and_never_paid_in_capital() -> None:
    observations = _observations().iloc[:3].drop(
        columns=["free_float_market_cap"]
    )
    observations["paid_in_capital_ntd"] = [1.0, 2.0, 3.0]
    grouped = build_pit_groupings(
        observations,
        sector_history=_sector_history().iloc[:3],
    )

    assert grouped["size_tier"].eq(INSUFFICIENT_FEATURES).all()
    assert grouped["size_percentile"].isna().all()
    assert grouped["liquidity_tier"].tolist() == ["low", "mid", "high"]


def test_concept_future_snapshot_and_current_backfill_are_insufficient() -> None:
    observations = pd.DataFrame(
        {
            "observation_date": ["2026-01-10", "2026-01-10", "2026-01-10"],
            "stock_id": ["2330", "2317", "2454"],
        }
    )
    concepts = pd.DataFrame(
        {
            "stock_id": ["2330", "2317", "2454", "2454"],
            "concept": ["AI", "SERVER", "IC_DESIGN", "EDGE_AI"],
            "snapshot_date": [
                "2026-01-11",
                "2026-01-01",
                "2026-01-05",
                "2026-01-05",
            ],
            "effective_date": [
                "2026-01-11",
                "2026-01-01",
                "2026-01-05",
                "2026-01-05",
            ],
            "available_date": [
                "2026-01-12",
                "2026-01-02",
                "2026-01-06",
                "2026-01-06",
            ],
            "membership_mode": [
                "point_in_time_snapshot",
                "static_current_backfill",
                "point_in_time_snapshot",
                "point_in_time_snapshot",
            ],
        }
    )

    attached = attach_concept_membership(observations, concepts)

    assert attached.loc[0, "concept_status"] == INSUFFICIENT_DATA
    assert attached.loc[1, "concept_status"] == INSUFFICIENT_DATA
    assert attached.loc[2, "concept_status"] == "point_in_time"
    assert attached.loc[2, "concepts"] == ("EDGE_AI", "IC_DESIGN")
    assert attached.loc[2, "concept_source_date"] <= attached.loc[
        2, "observation_date"
    ]


def test_market_regime_rejects_states_outside_six_allowed_combinations() -> None:
    observations = _observations().iloc[:3].copy()
    observations.loc[2, "market_trend"] = "bull"
    grouped = build_pit_groupings(
        observations,
        sector_history=_sector_history().iloc[:3],
    )

    assert grouped.loc[0, "market_regime"] == "trend_up_volatility_low"
    assert grouped.loc[1, "market_regime"] == "trend_flat_volatility_high"
    assert grouped.loc[2, "market_regime"] == INSUFFICIENT_FEATURES


def test_beta_binomial_partial_pool_shrinks_small_and_empty_groups() -> None:
    groups = pd.DataFrame(
        {
            "group": ["tiny", "large", "empty"],
            "successes": [1, 90, 0],
            "trials": [1, 100, 0],
        }
    )

    pooled = beta_binomial_partial_pool(groups, prior_strength=20.0)

    prior = float(pooled.loc[0, "prior_mean"])
    assert prior < pooled.loc[0, "pooled_rate"] < 1.0
    assert prior < pooled.loc[1, "pooled_rate"] < 0.9
    assert np.isclose(pooled.loc[2, "pooled_rate"], prior)
    assert pd.isna(pooled.loc[2, "raw_rate"])
    assert pooled.loc[2, "partial_pool_status"] == "prior_only"


def test_empty_inputs_preserve_schema_without_fabricating_groups() -> None:
    observations = _observations().iloc[:0]
    grouped = build_pit_groupings(
        observations,
        sector_history=_sector_history().iloc[:0],
    )
    pooled = beta_binomial_partial_pool(
        pd.DataFrame(columns=["successes", "trials"])
    )

    assert grouped.empty
    assert pooled.empty
    assert {
        "sector",
        "sector_within_percentile",
        "market_percentile",
        "size_tier",
        "liquidity_tier",
        "market_regime",
        "concept_status",
    }.issubset(grouped.columns)
    assert {"raw_rate", "pooled_rate", "partial_pool_status"}.issubset(
        pooled.columns
    )
