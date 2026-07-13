import pandas as pd
import pytest

from scripts.analyze_zhu_walkline_kd_d5_lead_snapshots import (
    assert_no_lookahead,
    build_lead_snapshots,
    prepare_adjusted_history,
)


def test_exact_prior_trading_offsets_skip_weekends() -> None:
    history = _history(pd.bdate_range("2026-01-02", periods=10))
    signal_date = pd.Timestamp("2026-01-16")
    signals = _signals(signal_date)

    rows = build_lead_snapshots(signals, history).set_index("lead_offset")

    assert rows.loc[1, "feature_date"] == "2026-01-15"
    assert rows.loc[3, "feature_date"] == "2026-01-13"
    assert rows.loc[5, "feature_date"] == "2026-01-09"


def test_signal_day_and_future_mutation_cannot_change_snapshots() -> None:
    dates = pd.bdate_range("2025-09-01", "2026-01-20")
    history = _history(dates)
    signals = _signals(pd.Timestamp("2026-01-16"))
    baseline = build_lead_snapshots(signals, history)
    mutated = history.copy()
    mask = mutated["date"].ge("2026-01-16")
    mutated.loc[mask, ["adj_open", "adj_high", "adj_low", "adj_close", "volume"]] = 999999.0

    changed = build_lead_snapshots(signals, mutated)

    pd.testing.assert_frame_equal(baseline, changed)
    assert_no_lookahead(changed)


def test_adjusted_history_kd_stays_bounded() -> None:
    history = _history(pd.bdate_range("2025-09-01", periods=100))

    result = prepare_adjusted_history(history)

    assert result["kd_k9"].between(0, 100).all()
    assert result["kd_d9"].between(0, 100).all()


def test_missing_fifth_prior_row_remains_empty() -> None:
    history = _history(pd.bdate_range("2026-01-02", periods=3))
    signals = _signals(pd.Timestamp("2026-01-07"))

    rows = build_lead_snapshots(signals, history).set_index("lead_offset")

    assert rows.loc[5, "feature_date"] == ""
    assert pd.isna(rows.loc[5, "adj_close"])


def test_adjusted_return_uses_adjusted_close() -> None:
    history = _history(pd.bdate_range("2025-09-01", periods=100))
    history["adj_close"] = pd.Series(range(100, 200), dtype=float)
    history["adj_open"] = history["adj_close"] - 1.0
    history["adj_high"] = history["adj_close"] + 1.0
    history["adj_low"] = history["adj_close"] - 2.0

    result = prepare_adjusted_history(history)

    assert result.iloc[-1]["daily_return_pct"] == pytest.approx((199 / 198 - 1) * 100)


def _signals(signal_date: pd.Timestamp) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asof_date": signal_date,
                "stock_id": "2330",
                "stock_name": "台積電",
                "d5_group": "D5_GAIN_GE_20",
                "d5_group_label": "D+5 >=20%",
                "d5_adjusted_return_pct": 25.0,
                "corporate_action_event_in_horizon": False,
            }
        ]
    )


def _history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    close = pd.Series(range(100, 100 + size), dtype=float)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "adj_open": close - 0.5,
            "adj_high": close + 1.0,
            "adj_low": close - 1.0,
            "adj_close": close,
            "volume": pd.Series(range(1000, 1000 + size), dtype=float),
            "adjustment_factor": [1.0] * size,
            "factor_event_count": [0] * size,
            "adjusted_data_asof": ["2026-07-13"] * size,
        }
    )
