from __future__ import annotations

import pandas as pd

from scripts.analyze_zhu_walkline_driver_peak_windows import (
    build_peak_window_rows,
    build_stock_peak_rows,
)


def test_build_peak_window_rows_uses_future_peak_and_context_dates() -> None:
    selected = pd.DataFrame(
        [
            {
                "asof_date": "2026-01-03",
                "stock_id": "1234",
                "stock_name": "測試",
                "sector": "電子零組件",
                "close": 10.0,
                "driver_score": 11,
                "forward_return_pct": 20.0,
            }
        ]
    )
    prices = pd.DataFrame(
        [
            {"date": "2026-01-01", "stock_id": "1234", "open": 8.0, "high": 8.5, "low": 7.8, "close": 8.2, "volume": 100, "close_location_in_bar": 0.6},
            {"date": "2026-01-02", "stock_id": "1234", "open": 9.0, "high": 9.5, "low": 8.9, "close": 9.3, "volume": 120, "close_location_in_bar": 0.7},
            {"date": "2026-01-03", "stock_id": "1234", "open": 10.0, "high": 99.0, "low": 9.8, "close": 10.0, "volume": 130, "close_location_in_bar": 0.1},
            {"date": "2026-01-04", "stock_id": "1234", "open": 11.0, "high": 12.0, "low": 10.5, "close": 11.5, "volume": 150, "close_location_in_bar": 0.7},
            {"date": "2026-01-05", "stock_id": "1234", "open": 12.0, "high": 15.0, "low": 11.5, "close": 14.0, "volume": 200, "close_location_in_bar": 0.7},
            {"date": "2026-01-06", "stock_id": "1234", "open": 13.0, "high": 13.5, "low": 12.5, "close": 13.0, "volume": 180, "close_location_in_bar": 0.5},
            {"date": "2026-01-07", "stock_id": "1234", "open": 12.8, "high": 13.0, "low": 12.0, "close": 12.5, "volume": 160, "close_location_in_bar": 0.5},
        ]
    )

    rows = build_peak_window_rows(
        selected,
        prices=prices,
        peak_horizon_trading_days=3,
        context_trading_days=1,
    )

    row = rows.iloc[0]
    assert row["peak_date"] == "2026-01-05"
    assert row["pre_week_date"] == "2026-01-04"
    assert row["post_week_date"] == "2026-01-06"
    assert row["trading_days_to_peak"] == 2
    assert row["asof_to_peak_high_return_pct"] == 50.0


def test_build_stock_peak_rows_deduplicates_to_highest_stock_peak() -> None:
    peak_rows = pd.DataFrame(
        [
            {
                "asof_date": "2026-01-03",
                "stock_id": "1234",
                "stock_name": "測試",
                "sector": "電子零組件",
                "close": 10.0,
                "driver_score": 11,
                "forward_return_pct": 5.0,
                "peak_date": "2026-01-06",
                "peak_high": 12.0,
                "peak_close": 11.5,
                "peak_volume": 100,
                "trading_days_to_peak": 3,
                "pre_week_date": "2026-01-05",
                "pre_week_close": 11.0,
                "post_week_date": "2026-01-07",
                "post_week_close": 10.5,
                "asof_to_peak_high_return_pct": 20.0,
                "pre_week_to_peak_high_return_pct": 9.0,
                "peak_high_to_post_week_close_pct": -12.5,
                "post_week_max_drawdown_from_peak_high_pct": -15.0,
                "post_week_close_from_asof_pct": 5.0,
                "peak_day_close_location_in_bar": 0.6,
                "peak_day_upper_shadow_pct": 10.0,
                "peak_day_close_from_high_pct": -4.0,
                "peak_volume_vs_pre_week_avg": 2.0,
                "peak_timing_bucket": "D01_05",
                "peak_gain_bucket": "GAIN_20_30PCT",
                "post_peak_fade_bucket": "FADE_NEG10_15PCT",
                "peak_window_pattern": "EARLY_SPIKE_FADE",
            },
            {
                "asof_date": "2026-01-04",
                "stock_id": "1234",
                "stock_name": "測試",
                "sector": "電子零組件",
                "close": 11.0,
                "driver_score": 12,
                "forward_return_pct": 15.0,
                "peak_date": "2026-01-09",
                "peak_high": 20.0,
                "peak_close": 19.0,
                "peak_volume": 200,
                "trading_days_to_peak": 5,
                "pre_week_date": "2026-01-08",
                "pre_week_close": 18.0,
                "post_week_date": "2026-01-10",
                "post_week_close": 19.5,
                "asof_to_peak_high_return_pct": 81.818181,
                "pre_week_to_peak_high_return_pct": 11.111111,
                "peak_high_to_post_week_close_pct": -2.5,
                "post_week_max_drawdown_from_peak_high_pct": -5.0,
                "post_week_close_from_asof_pct": 77.272727,
                "peak_day_close_location_in_bar": 0.8,
                "peak_day_upper_shadow_pct": 5.0,
                "peak_day_close_from_high_pct": -5.0,
                "peak_volume_vs_pre_week_avg": 3.0,
                "peak_timing_bucket": "D01_05",
                "peak_gain_bucket": "GAIN_GT_50PCT",
                "post_peak_fade_bucket": "FADE_NEG0_5PCT",
                "peak_window_pattern": "STRONG_CLOSE_HOLDS_NEAR_HIGH",
            },
        ]
    )

    rows = build_stock_peak_rows(peak_rows)

    assert len(rows) == 1
    row = rows.iloc[0]
    assert row["selected_signal_count"] == 2
    assert row["first_asof_date"] == "2026-01-03"
    assert row["last_asof_date"] == "2026-01-04"
    assert row["source_asof_date"] == "2026-01-04"
    assert row["peak_high"] == 20.0
