import pytest

from abc_quant.metrics.performance import (
    annual_volatility,
    cagr,
    max_drawdown,
    performance_summary,
    sharpe_ratio,
    total_return,
)


def test_performance_metrics_on_simple_return_series() -> None:
    returns = [0.10, 0.0, -0.05]

    assert total_return(returns) == pytest.approx(0.045)
    assert cagr(returns, periods_per_year=3) == pytest.approx(0.045)
    assert annual_volatility(returns, periods_per_year=1) == pytest.approx(0.062360956446)
    assert sharpe_ratio(returns, periods_per_year=1) == pytest.approx(0.267261241912)
    assert max_drawdown(returns) == pytest.approx(-0.05)


def test_performance_summary_contains_required_metrics() -> None:
    summary = performance_summary([0.01, 0.02, -0.01], periods_per_year=3)

    assert set(summary) == {
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe_ratio",
        "max_drawdown",
    }
