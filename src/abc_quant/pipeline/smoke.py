"""End-to-end deterministic smoke pipeline."""

from __future__ import annotations

from typing import Final

import pandas as pd

from abc_quant.data.sample import sample_market_data
from abc_quant.data.validation import validate_market_data
from abc_quant.features.price_volume import add_price_volume_features
from abc_quant.labels.returns import add_forward_return_label
from abc_quant.metrics.performance import performance_summary

SMOKE_FEATURE_COLUMNS: Final[tuple[str, ...]] = (
    "price_momentum_1d",
    "price_momentum_3d",
    "price_volatility_3d",
    "volume_average_3d",
)
SMOKE_LABEL_COLUMN: Final[str] = "label_forward_return_3d_entry_lag_1d"
SMOKE_METRIC_KEYS: Final[tuple[str, ...]] = (
    "total_return",
    "cagr",
    "annual_volatility",
    "sharpe_ratio",
    "max_drawdown",
)


def build_smoke_frame(market_data: pd.DataFrame | None = None) -> pd.DataFrame:
    """Validate fixture data, add smoke features, and add one forward label."""
    source = sample_market_data() if market_data is None else market_data
    validated = validate_market_data(source)
    featured = add_price_volume_features(
        validated,
        momentum_windows=(1, 3),
        volatility_windows=(3,),
        volume_windows=(3,),
    )
    return add_forward_return_label(
        featured,
        horizon=3,
        entry_lag=1,
        label_col=SMOKE_LABEL_COLUMN,
    )


def run_smoke_pipeline() -> dict[str, object]:
    """Run the deterministic local smoke pipeline and return summary evidence."""
    frame = build_smoke_frame()
    metrics = performance_summary(_average_daily_returns(frame))

    return {
        "row_count": int(len(frame)),
        "ticker_count": int(frame["ticker"].nunique()),
        "rows_per_ticker": {
            str(ticker): int(count) for ticker, count in frame.groupby("ticker").size().items()
        },
        "feature_columns": SMOKE_FEATURE_COLUMNS,
        "label_column": SMOKE_LABEL_COLUMN,
        "label_non_null_count": int(frame[SMOKE_LABEL_COLUMN].notna().sum()),
        "metric_keys": tuple(metrics),
        "metrics": metrics,
        "first_momentum_is_null_by_ticker": _first_feature_nulls(frame, "price_momentum_1d"),
    }


def _average_daily_returns(frame: pd.DataFrame) -> pd.Series:
    ticker_returns = frame.groupby("ticker", group_keys=False, sort=False)["close"].pct_change()
    return (
        frame.assign(_sample_return=ticker_returns)
        .groupby("date")["_sample_return"]
        .mean()
        .dropna()
    )


def _first_feature_nulls(frame: pd.DataFrame, feature_col: str) -> dict[str, bool]:
    return {
        str(ticker): bool(pd.isna(group.iloc[0][feature_col]))
        for ticker, group in frame.groupby("ticker", sort=True)
    }
