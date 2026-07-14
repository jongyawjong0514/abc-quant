from __future__ import annotations

import pandas as pd
import pytest

from scripts.analyze_zhu_walkline_shadow_decision_surface import (
    attach_market_state,
    build_group_metrics,
    build_market_regime_coverage,
    expected_return_validation_status,
    validate_modeling_rows,
)


def test_validate_modeling_rows_rejects_future_technical_source() -> None:
    rows = _modeling_fixture()
    rows.loc[0, "technical_source_date"] = "2026-01-03"
    with pytest.raises(ValueError, match="after observation"):
        validate_modeling_rows(rows)


def test_market_state_uses_only_six_allowed_states() -> None:
    rows = _modeling_fixture()
    observations = rows[
        ["asof_date", "observation_date", "stock_id", "split"]
    ].copy()
    output = attach_market_state(
        observations,
        market_rows=validate_modeling_rows(rows).assign(
            return_20d=lambda frame: frame["return_20d"] * 100.0
        ),
        trend_threshold_pct=2.0,
    )
    assert set(output["market_trend"]) <= {"up", "flat", "down"}
    assert set(output["market_volatility"]) <= {"high", "low"}


def test_group_metrics_partial_pool_and_size_insufficient() -> None:
    predictions = pd.DataFrame(
        {
            "stock_id": ["1101", "1102", "2330", "2303"],
            "sector": ["cement", "cement", "semiconductor", "semiconductor"],
            "liquidity_tier": ["low", "mid", "high", "high"],
            "market_regime": ["trend_up_volatility_low"] * 4,
            "size_tier": ["INSUFFICIENT_FEATURES"] * 4,
            "p_ge10": [0.1, 0.2, 0.3, 0.4],
            "p_tail_loss_le_minus3": [0.4, 0.3, 0.2, 0.1],
        }
    )
    metrics = build_group_metrics(
        predictions,
        pd.Series([-2.0, 12.0, 3.0, 25.0]),
        minimum_group_rows=2,
    )
    sector = metrics[metrics["dimension"].eq("sector")]
    assert sector["pooled_rate"].between(0, 1).all()
    assert sector["prior_mean"].eq(0.5).all()
    size = metrics[metrics["dimension"].eq("size_tier")]
    assert size.iloc[0]["group"] == "INSUFFICIENT_FEATURES"


def test_expected_return_status_fails_closed_on_weak_holdout() -> None:
    metrics = pd.DataFrame(
        {
            "split": ["HOLDOUT"],
            "correlation": [0.001],
            "mean_bias": [2.1],
        }
    )

    assert expected_return_validation_status(metrics) == "DIAGNOSTIC_UNTRUSTED"


def test_expected_return_status_accepts_bounded_holdout_edge() -> None:
    metrics = pd.DataFrame(
        {
            "split": ["HOLDOUT"],
            "correlation": [0.12],
            "mean_bias": [0.4],
        }
    )

    assert expected_return_validation_status(metrics) == "HOLDOUT_VALIDATED"


def test_market_regime_coverage_keeps_zero_row_states_visible() -> None:
    coverage = build_market_regime_coverage(
        pd.DataFrame(
            {"market_regime": ["trend_up_volatility_high"] * 3}
        )
    )

    assert len(coverage) == 6
    assert coverage["rows"].sum() == 3
    assert (~coverage["evaluated"]).sum() == 5


def _modeling_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asof_date": ["2026-01-02", "2026-01-02", "2026-05-11", "2026-05-11"],
            "observation_date": [
                "2026-01-02",
                "2026-01-02",
                "2026-05-11",
                "2026-05-11",
            ],
            "stock_id": ["1101", "1102", "2330", "2303"],
            "split": ["DISCOVERY", "DISCOVERY", "HOLDOUT", "HOLDOUT"],
            "technical_source_date": [
                "2026-01-02",
                "2026-01-02",
                "2026-05-11",
                "2026-05-11",
            ],
            "net_return_pct": [-1.0, 12.0, 3.0, 25.0],
            "return_20d": [-0.05, 0.10, 0.03, 0.05],
            "volatility_20d_pct": [2.0, 3.0, 2.5, 4.0],
        }
    )
