from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from abc_quant.validation.grouped_shadow_validation import (
    beta_posterior_summary,
    build_grouped_strategy_metrics,
    estimate_beta_binomial_prior,
)


def test_beta_prior_and_posterior_shrink_small_groups_more() -> None:
    prior = estimate_beta_binomial_prior(
        pd.Series([1, 8, 20]),
        pd.Series([1, 20, 100]),
        fallback_strength=10.0,
    )

    small = beta_posterior_summary(1, 1, prior)
    large = beta_posterior_summary(80, 100, prior)

    assert 0.0 < prior.mean < 1.0
    assert prior.strength >= 10.0
    assert abs(small["posterior_precision"] - prior.mean) < abs(1.0 - prior.mean)
    assert abs(large["posterior_precision"] - 0.8) < abs(small["posterior_precision"] - 1.0)
    assert 0.0 <= small["posterior_precision_lower"]
    assert small["posterior_precision_upper"] <= 1.0


def test_grouped_metrics_use_group_base_and_do_not_rank_empty_as_certain() -> None:
    frame = pd.DataFrame(
        {
            "asof_date": pd.date_range("2026-05-01", periods=8),
            "stock_id": ["0001", "0002"] * 4,
            "sector": ["A"] * 4 + ["B"] * 4,
            "target_gain_ge10": [1, 0, 1, 0, 0, 0, 1, 0],
            "net_return_pct": [12.0, -2.0, 11.0, -4.0, 2.0, -1.0, 13.0, -5.0],
            "signal": [True, True, False, False, False, False, False, False],
        }
    )

    metrics, priors = build_grouped_strategy_metrics(
        frame,
        group_column="sector",
        strategies={"ALL": None, "SIGNAL": "signal"},
        fallback_prior_strength=5.0,
    )

    assert set(priors["strategy"]) == {"ALL", "SIGNAL"}
    signal_a = metrics[(metrics["strategy"] == "SIGNAL") & (metrics["sector"] == "A")].iloc[0]
    signal_b = metrics[(metrics["strategy"] == "SIGNAL") & (metrics["sector"] == "B")].iloc[0]
    assert signal_a["eligible_gain_rate"] == pytest.approx(0.5)
    assert signal_a["selected_rows"] == 2
    assert signal_a["selected_gain_rate"] == pytest.approx(0.5)
    assert signal_a["precision_lift_vs_group_base"] == pytest.approx(1.0)
    assert signal_b["selected_rows"] == 0
    assert np.isnan(signal_b["selected_gain_rate"])
    assert 0.0 < signal_b["posterior_precision"] < 1.0


@pytest.mark.parametrize(
    ("successes", "totals"),
    [([1], [0]), ([2], [1]), ([1, 2], [3])],
)
def test_beta_prior_rejects_invalid_or_empty_groups(
    successes: list[int], totals: list[int]
) -> None:
    with pytest.raises(ValueError):
        estimate_beta_binomial_prior(successes, totals)
