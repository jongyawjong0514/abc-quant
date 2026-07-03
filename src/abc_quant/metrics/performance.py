"""Backtest performance metrics."""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt

import numpy as np
import pandas as pd


def total_return(periodic_returns: Iterable[float]) -> float:
    """Return compounded total return from periodic strategy returns."""
    returns = _clean_returns(periodic_returns)
    if returns.empty:
        return 0.0
    return float((1.0 + returns).prod() - 1.0)


def cagr(periodic_returns: Iterable[float], *, periods_per_year: int = 252) -> float:
    """Return compound annual growth rate from periodic returns."""
    returns = _clean_returns(periodic_returns)
    if returns.empty:
        return 0.0
    ending_growth = 1.0 + total_return(returns)
    if ending_growth <= 0:
        return float("nan")
    years = len(returns) / periods_per_year
    return float(ending_growth ** (1.0 / years) - 1.0)


def annual_volatility(periodic_returns: Iterable[float], *, periods_per_year: int = 252) -> float:
    """Return annualized volatility using population standard deviation."""
    returns = _clean_returns(periodic_returns)
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=0) * sqrt(periods_per_year))


def sharpe_ratio(
    periodic_returns: Iterable[float],
    *,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> float:
    """Return annualized Sharpe ratio from periodic returns."""
    returns = _clean_returns(periodic_returns)
    if returns.empty:
        return 0.0
    period_risk_free = risk_free_rate / periods_per_year
    excess = returns - period_risk_free
    volatility = excess.std(ddof=0)
    if volatility == 0 or np.isclose(volatility, 0.0):
        return 0.0
    return float(excess.mean() / volatility * sqrt(periods_per_year))


def max_drawdown(periodic_returns: Iterable[float]) -> float:
    """Return the worst peak-to-trough drawdown from periodic returns."""
    returns = _clean_returns(periodic_returns)
    if returns.empty:
        return 0.0
    equity = (1.0 + returns).cumprod()
    running_peak = equity.cummax()
    drawdowns = equity / running_peak - 1.0
    return float(drawdowns.min())


def performance_summary(
    periodic_returns: Iterable[float],
    *,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """Return the first-pass backtest metrics required by the task."""
    returns = _clean_returns(periodic_returns)
    return {
        "total_return": total_return(returns),
        "cagr": cagr(returns, periods_per_year=periods_per_year),
        "annual_volatility": annual_volatility(returns, periods_per_year=periods_per_year),
        "sharpe_ratio": sharpe_ratio(
            returns, periods_per_year=periods_per_year, risk_free_rate=risk_free_rate
        ),
        "max_drawdown": max_drawdown(returns),
    }


def _clean_returns(periodic_returns: Iterable[float]) -> pd.Series:
    returns = pd.Series(periodic_returns, dtype="float64").replace([np.inf, -np.inf], np.nan)
    return returns.dropna()
