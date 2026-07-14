from __future__ import annotations

import pandas as pd

from abc_quant.features.early_observation_score import EarlyObservationScoreConfig
from scripts.score_zhu_walkline_early_lowpoint import (
    assert_live_output_contract,
    build_daily_early_watchlist,
    build_early_feature_history,
    ensure_live_output_schema,
)


def test_daily_watchlist_keeps_lower_shadow_contextual_only() -> None:
    history = _history_fixture(return_5d_pct=3.0)

    rows = build_daily_early_watchlist(
        history,
        asof_date="2026-01-09",
        market_calendar=history["date"],
        score_config=EarlyObservationScoreConfig(),
        minimum_core_score=30.0,
        avoid_chase_return_5d_pct=8.0,
        maximum_distance_from_low_pct=8.0,
    )

    assert len(rows) == 1
    row = rows.iloc[0]
    assert row["early_observation_stage"] == "D1_EARLY_OBSERVATION"
    assert row["d5_selling_pressure_reason"] == "low_volume_bullish_context"
    assert row["d5_volume_ratio_20"] == 0.45
    assert row["d5_lower_shadow_reason"] == "bullish_lower_shadow_support"
    assert bool(row["lower_shadow_contextual_only"])
    assert row["action"] == "watch_only"
    assert_live_output_contract(rows)


def test_daily_watchlist_marks_already_extended_stock_avoid_chase() -> None:
    history = _history_fixture(return_5d_pct=9.0)

    rows = build_daily_early_watchlist(
        history,
        asof_date="2026-01-09",
        market_calendar=history["date"],
        score_config=EarlyObservationScoreConfig(),
        minimum_core_score=30.0,
        avoid_chase_return_5d_pct=8.0,
        maximum_distance_from_low_pct=8.0,
    )

    assert len(rows) == 1
    assert bool(rows.iloc[0]["avoid_chase"])
    assert rows.iloc[0]["action"] == "avoid_chase"
    assert rows.iloc[0]["avoid_chase_reason"] == "return_5d_extended"


def test_missing_market_session_cannot_be_relabelled_as_d3_or_d1() -> None:
    candidate = _history_fixture(return_5d_pct=3.0)
    candidate = candidate[candidate["date"].ne(pd.Timestamp("2026-01-07"))]
    calendar_only = _history_fixture(return_5d_pct=3.0).assign(
        stock_id="9999",
        ma20_slope_pct=float("nan"),
    )

    rows = build_daily_early_watchlist(
        pd.concat([candidate, calendar_only], ignore_index=True),
        asof_date="2026-01-09",
        market_calendar=calendar_only["date"],
        score_config=EarlyObservationScoreConfig(),
        minimum_core_score=30.0,
        avoid_chase_return_5d_pct=8.0,
        maximum_distance_from_low_pct=8.0,
    )

    assert "2464" not in set(rows["stock_id"])


def test_live_contract_rejects_outcome_and_label_columns() -> None:
    rows = build_daily_early_watchlist(
        _history_fixture(return_5d_pct=3.0),
        asof_date="2026-01-09",
        market_calendar=_history_fixture(return_5d_pct=3.0)["date"],
        score_config=EarlyObservationScoreConfig(),
        minimum_core_score=30.0,
        avoid_chase_return_5d_pct=8.0,
        maximum_distance_from_low_pct=8.0,
    )

    for forbidden in (
        "outcome_class",
        "label_gain",
        "actual_return",
        "exit_price",
        "d5_adjusted_return_pct",
        "d5_close_date",
        "return_d5_pct",
    ):
        with_forbidden = rows.assign(**{forbidden: 1})
        try:
            assert_live_output_contract(with_forbidden)
        except ValueError:
            continue
        raise AssertionError(f"forbidden column passed live contract: {forbidden}")

    try:
        ensure_live_output_schema(rows.assign(unknown_evaluator_alias=1))
    except ValueError:
        pass
    else:
        raise AssertionError("live schema allowlist accepted an unknown column")


def test_tight_body_window_uses_five_prior_sessions_not_current_day() -> None:
    dates = pd.bdate_range("2026-01-01", periods=7)
    prices = pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2464"] * 7,
            "open": [100.0] * 7,
            "high": [103.0] * 7,
            "low": [99.0] * 7,
            "close": [102.0] * 5 + [100.5, 101.0],
            "volume": [1000.0] * 7,
        }
    )

    history = build_early_feature_history(
        prices,
        asof_date="2026-01-09",
        trailing_body_window=5,
    )

    value = history.loc[
        history["date"].eq(pd.Timestamp("2026-01-08")),
        "pre5_min_abs_open_close_pct",
    ].iloc[0]
    assert value == 2.0


def test_context_points_cannot_satisfy_core_membership_gate() -> None:
    rows = build_daily_early_watchlist(
        _history_fixture(return_5d_pct=3.0),
        asof_date="2026-01-05",
        market_calendar=_history_fixture(return_5d_pct=3.0)["date"],
        score_config=EarlyObservationScoreConfig(),
        minimum_core_score=36.0,
        avoid_chase_return_5d_pct=8.0,
        maximum_distance_from_low_pct=8.0,
    )

    assert rows.empty


def _history_fixture(*, return_5d_pct: float) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=7)
    rows = pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2464"] * len(dates),
            "close": [100.0, 99.0, 98.0, 98.5, 99.0, 99.5, 101.0],
            "daily_return_pct": [-0.2, -0.5, -1.0, 0.2, 0.4, 0.3, 1.0],
            "return_5d_pct": [0.0] * 6 + [return_5d_pct],
            "distance_from_trailing_5d_low_pct": [2.0] * 7,
            "volume_ratio_20": [0.8, 0.7, 0.45, 0.6, 0.50, 0.6, 0.80],
            "volume_ratio_slope": [0.1, 0.0, -0.1, 0.0, 0.1, 0.1, 0.1],
            "volume_slope_acceleration": [0.0, 0.0, 0.1, 0.0, 0.2, 0.0, 0.2],
            "ma20_slope_pct": [0.2] * 7,
            "upper_shadow_body_ratio": [0.5] * 7,
            "consecutive_down_days": [0, 1, 1, 0, 0, 0, 0],
            "pre5_min_abs_open_close_pct": [0.8] * 7,
            "lower_shadow_body_ratio": [2.0] * 7,
            "lower_shadow_pct": [1.2] * 7,
            "close_location_in_bar": [0.7] * 7,
            "volume_spike_selloff": [False] * 7,
            "price_stabilized": [True] * 7,
            "kd_k_change_1d": [0.5] * 7,
            "close_to_ma20_pct": [0.5] * 7,
            "avg_turnover_20_twd": [50_000_000.0] * 7,
        }
    )
    return rows
