from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from abc_quant.features.d10_factor_panel import (
    INSTITUTIONAL_FACTOR_COLUMNS,
    TECHNICAL_FACTOR_COLUMNS,
    assert_factor_panel_point_in_time,
    build_d10_factor_panel,
    build_institutional_factor_panel,
    build_technical_factor_panel,
)


def test_appending_future_prices_does_not_change_technical_history() -> None:
    dates = pd.bdate_range("2026-01-02", periods=35)
    history = _price_history(dates)
    cutoff = dates[29]

    baseline = build_technical_factor_panel(
        history[history["date"].le(cutoff)],
        asof_date=cutoff,
    )
    mutated = history.copy()
    future = mutated["date"].gt(cutoff)
    mutated.loc[future, ["open", "high", "low", "close"]] = 999_999.0
    mutated.loc[future, "volume"] = 999_999_999.0
    with_future = build_technical_factor_panel(mutated, asof_date=cutoff)

    pd.testing.assert_frame_equal(baseline, with_future)
    assert set(TECHNICAL_FACTOR_COLUMNS).issubset(with_future.columns)
    assert_factor_panel_point_in_time(with_future)


def test_same_day_institutional_flow_is_strictly_lagged() -> None:
    dates = pd.bdate_range("2026-02-02", periods=12)
    price = _price_history(dates, volume=np.full(len(dates), 1_000.0))
    institutional = _institutional_history(dates)
    institutional.loc[
        institutional["date"].eq(dates[-1]), "foreign_net_buy_shares"
    ] = 900_000.0

    panel = build_institutional_factor_panel(
        institutional,
        price,
        asof_date=dates[-1],
    )
    row = panel.loc[panel["observation_date"].eq(dates[-1])].iloc[0]

    assert row["institutional_source_date"] == dates[-2]
    assert row["foreign_net_volume_ratio_1d_pct"] == pytest.approx(1.0)
    assert row["foreign_net_volume_ratio_1d_pct"] != pytest.approx(90_000.0)
    assert_factor_panel_point_in_time(panel)


def test_volume_slope_and_acceleration_have_expected_direction() -> None:
    dates = pd.bdate_range("2026-03-02", periods=25)
    volume = np.array(
        [100.0] * 15
        + [110.0, 130.0, 160.0, 200.0, 250.0]
        + [240.0, 220.0, 190.0, 150.0, 100.0]
    )
    panel = build_technical_factor_panel(
        _price_history(dates, volume=volume),
        asof_date=dates[-1],
    ).set_index("observation_date")

    accelerating = panel.loc[dates[19]]
    falling = panel.loc[dates[-1]]
    assert accelerating["volume_slope_3"] > 0.0
    assert accelerating["volume_slope_accel_3"] > 0.0
    assert falling["volume_slope_3"] < 0.0
    assert falling["volume_slope_accel_3"] < 0.0


def test_combined_panel_never_exports_raw_institutional_shares() -> None:
    dates = pd.bdate_range("2026-04-01", periods=25)
    panel = build_d10_factor_panel(
        _price_history(dates),
        institutional_history=_institutional_history(dates),
        asof_date=dates[-1],
    )

    assert set(INSTITUTIONAL_FACTOR_COLUMNS).issubset(panel.columns)
    assert not any("shares" in column.lower() for column in panel.columns)
    assert not any(
        "foreign_net_buy_shares" in column.lower() for column in panel.columns
    )
    assert_factor_panel_point_in_time(panel)


def test_zero_volume_ratios_remain_missing_not_infinite() -> None:
    dates = pd.bdate_range("2026-05-04", periods=25)
    volume = np.full(len(dates), 1_000.0)
    volume[-2:] = 0.0
    panel = build_d10_factor_panel(
        _price_history(dates, volume=volume),
        institutional_history=_institutional_history(dates),
        asof_date=dates[-1],
    )
    numeric = panel.select_dtypes(include=[np.number])

    assert not np.isinf(numeric.to_numpy()).any()
    last = panel.iloc[-1]
    assert np.isnan(last["foreign_net_volume_ratio_1d_pct"])


def test_point_in_time_assertion_rejects_same_day_institutional_source() -> None:
    panel = pd.DataFrame(
        {
            "observation_date": ["2026-06-01"],
            "stock_id": ["2330"],
            "institutional_source_date": ["2026-06-01"],
        }
    )

    with pytest.raises(AssertionError, match="strictly before"):
        assert_factor_panel_point_in_time(panel)


def _price_history(
    dates: pd.DatetimeIndex,
    *,
    volume: np.ndarray | None = None,
) -> pd.DataFrame:
    size = len(dates)
    close = 100.0 + np.linspace(0.0, 12.0, size) + np.sin(np.arange(size) / 2.0)
    selected_volume = (
        np.linspace(1_000.0, 2_000.0, size) if volume is None else np.asarray(volume)
    )
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": selected_volume,
        }
    )


def _institutional_history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "foreign_net_buy_shares": np.full(size, 10.0),
            "trust_net_buy_shares": np.full(size, 5.0),
            "dealer_net_buy_shares": np.full(size, -2.0),
            "institutional_net_buy_shares": np.full(size, 13.0),
        }
    )
