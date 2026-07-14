import numpy as np
import pandas as pd
import pytest

from abc_quant.features.pre_signal_features import (
    build_pre_signal_feature_frame,
    build_univariate_holdout_reference,
    compare_gain_groups_with_loss,
)
from abc_quant.features.shadow_strength import (
    ShadowStrengthRule,
    apply_shadow_strength_score,
)
from scripts.analyze_zhu_walkline_kd_d5_pre_signal_features import assert_no_lookahead


def test_pre_signal_features_ignore_signal_day_and_future_rows() -> None:
    signals = pd.DataFrame([{"asof_date": "2026-01-12", "stock_id": "2330"}])
    dates = pd.bdate_range("2025-12-01", "2026-01-14")
    price = _price_history(dates)
    institutional = _institutional_history(dates)
    holder = _holder_history(dates)
    margin = _margin_history(dates)
    main_force = pd.DataFrame({"2330": np.arange(len(dates), dtype=float)}, index=dates)
    broker = pd.DataFrame({"2330": np.arange(len(dates), dtype=float)}, index=dates)

    baseline = build_pre_signal_feature_frame(
        signals,
        market_calendar=dates,
        price_history=price[price["date"] < "2026-01-12"],
        institutional_history=institutional[institutional["date"] < "2026-01-12"],
        holder_history=holder[holder["date"] < "2026-01-12"],
        margin_history=margin[margin["trade_date"] < "2026-01-12"],
        main_force_panel=main_force[main_force.index < "2026-01-12"],
        broker_count_panel=broker[broker.index < "2026-01-12"],
    )

    mutated_price = price.copy()
    mutated_price.loc[mutated_price["date"] >= "2026-01-12", "close"] = 999999.0
    mutated_institutional = institutional.copy()
    mutated_institutional.loc[
        mutated_institutional["date"] >= "2026-01-12", "foreign_net_buy_shares"
    ] = 999999999.0
    mutated_main_force = main_force.copy()
    mutated_main_force.loc[mutated_main_force.index >= "2026-01-12", "2330"] = 999999.0

    mutated = build_pre_signal_feature_frame(
        signals,
        market_calendar=dates,
        price_history=mutated_price,
        institutional_history=mutated_institutional,
        holder_history=holder,
        margin_history=margin,
        main_force_panel=mutated_main_force,
        broker_count_panel=broker,
    )

    pd.testing.assert_frame_equal(baseline, mutated)
    assert_no_lookahead(mutated)


def test_prior_five_day_tight_body_feature_uses_exact_1_2_percent_boundary() -> None:
    dates = pd.bdate_range("2026-01-02", periods=6)
    price = _price_history(dates)
    price["open"] = 100.0
    price["close"] = [105.0, 101.2, 98.8, 101.3, 100.0, 999.0]
    signals = pd.DataFrame([{"asof_date": dates[-1], "stock_id": "2330"}])

    row = build_pre_signal_feature_frame(
        signals,
        market_calendar=dates,
        price_history=price,
        institutional_history=pd.DataFrame(),
        holder_history=pd.DataFrame(),
        margin_history=pd.DataFrame(),
    ).iloc[0]

    assert row["pre5_tight_body_count_le_1_2pct"] == 3
    assert bool(row["pre5_tight_body_exists_le_1_2pct"])
    assert row["pre5_min_abs_open_close_pct"] == pytest.approx(0.0)


def test_holder_and_margin_require_strict_availability_dates() -> None:
    signals = pd.DataFrame([{"asof_date": "2026-01-12", "stock_id": "2330"}])
    holder = pd.DataFrame(
        {
            "date": ["2026-01-09", "2026-01-12"],
            "stock_id": ["2330", "2330"],
            "holder_source_date": ["2026-01-09", "2026-01-12"],
            "alignment_status": ["ok", "ok"],
            "source_kind": ["official", "official"],
            "big_holder_ratio_1000_lots_pct": [40.0, 99.0],
            "big_holder_count_1000_lots": [10.0, 99.0],
        }
    )
    margin = pd.DataFrame(
        {
            "trade_date": ["2026-01-09", "2026-01-10"],
            "stock_id": ["2330", "2330"],
            "margin_balance": [100.0, 999.0],
            "available_date": ["2026-01-09", "2026-01-12"],
        }
    )

    row = build_pre_signal_feature_frame(
        signals,
        market_calendar=pd.to_datetime(["2026-01-08", "2026-01-09"]),
        price_history=_price_history(pd.to_datetime(["2026-01-08", "2026-01-09"])),
        institutional_history=pd.DataFrame(),
        holder_history=holder,
        margin_history=margin,
    ).iloc[0]

    assert row["pre_holder_source_date"] == "2026-01-09"
    assert row["pre_big_holder_ratio_1000_lots_pct"] == pytest.approx(40.0)
    assert row["pre_margin_available_date"] == "2026-01-09"
    assert row["pre_margin_balance"] == pytest.approx(100.0)


def test_stale_daily_sources_fail_closed_instead_of_reusing_old_values() -> None:
    signals = pd.DataFrame([{"asof_date": "2026-01-12", "stock_id": "2330"}])
    price = _price_history(pd.to_datetime(["2026-01-08", "2026-01-09"]))
    institutional = _institutional_history(pd.to_datetime(["2026-01-08"]))
    main_force = pd.DataFrame(
        {"2330": [100.0]}, index=pd.to_datetime(["2026-01-08"])
    )
    margin = pd.DataFrame(
        {
            "trade_date": ["2026-01-08"],
            "stock_id": ["2330"],
            "margin_balance": [1000.0],
            "available_date": ["2026-01-08"],
        }
    )

    row = build_pre_signal_feature_frame(
        signals,
        market_calendar=pd.to_datetime(["2026-01-08", "2026-01-09"]),
        price_history=price,
        institutional_history=institutional,
        holder_history=pd.DataFrame(),
        margin_history=margin,
        main_force_panel=main_force,
    ).iloc[0]

    assert row["pre_price_source_date"] == "2026-01-09"
    assert np.isnan(row["pre_institutional_source_date"])
    assert np.isnan(row["pre_main_force_source_date"])
    assert np.isnan(row["pre_main_force_net_lots_1d"])
    assert np.isnan(row["pre_margin_available_date"])
    assert np.isnan(row["pre_margin_balance_change_5d_pct"])


def test_independent_market_calendar_blocks_self_anchored_stale_price() -> None:
    signals = pd.DataFrame([{"asof_date": "2026-01-12", "stock_id": "2330"}])
    stale_date = pd.to_datetime(["2026-01-08"])
    price = _price_history(stale_date)
    main_force = pd.DataFrame({"2330": [100.0]}, index=stale_date)
    margin = pd.DataFrame(
        {
            "trade_date": stale_date,
            "stock_id": ["2330"],
            "margin_balance": [1000.0],
            "available_date": stale_date,
        }
    )

    features = build_pre_signal_feature_frame(
        signals,
        market_calendar=pd.to_datetime(["2026-01-08", "2026-01-09"]),
        price_history=price,
        institutional_history=pd.DataFrame(),
        holder_history=pd.DataFrame(),
        margin_history=margin,
        main_force_panel=main_force,
    )
    rules = [
        ShadowStrengthRule(
            "main_force",
            "pre_main_force_net_lots_1d",
            "pre_main_force_source_date",
            "HIGHER",
            0.0,
        ),
        ShadowStrengthRule(
            "no_upper_tail",
            "pre5_upper_tail_count",
            "pre_price_source_date",
            "LOWER",
            0.0,
        ),
        ShadowStrengthRule(
            "volume_ratio",
            "pre_day_volume_ratio_20",
            "pre_price_source_date",
            "HIGHER",
            0.0,
        ),
        ShadowStrengthRule(
            "margin_change",
            "pre_margin_balance_change_5d_pct",
            "pre_margin_available_date",
            "HIGHER",
            0.0,
        ),
    ]
    scored = apply_shadow_strength_score(features, rules=rules).iloc[0]

    assert np.isnan(scored["pre_price_source_date"])
    assert np.isnan(scored["pre_main_force_source_date"])
    assert np.isnan(scored["pre_margin_available_date"])
    assert not bool(scored["shadow_strength_complete"])
    assert scored["shadow_strength_score_status"] == "INSUFFICIENT_FEATURES"


def test_missing_chip_sources_remain_missing_instead_of_zero() -> None:
    row = build_pre_signal_feature_frame(
        pd.DataFrame([{"asof_date": "2026-01-12", "stock_id": "2330"}]),
        market_calendar=pd.to_datetime(["2026-01-09"]),
        price_history=pd.DataFrame(),
        institutional_history=pd.DataFrame(),
        holder_history=pd.DataFrame(),
        margin_history=pd.DataFrame(),
    ).iloc[0]

    assert np.isnan(row["pre_foreign_net_volume_ratio_5d_pct"])
    assert np.isnan(row["pre_main_force_net_volume_ratio_5d_pct"])
    assert np.isnan(row["pre_big_holder_ratio_1000_lots_pct"])
    assert np.isnan(row["pre_margin_balance"])


def test_univariate_reference_freezes_discovery_threshold_for_holdout() -> None:
    rows = pd.DataFrame(
        {
            "asof_date": [
                "2026-01-02",
                "2026-01-05",
                "2026-01-06",
                "2026-01-07",
                "2026-04-01",
                "2026-04-02",
                "2026-04-03",
                "2026-04-06",
            ],
            "d5_group": [
                "D5_LOSS",
                "D5_LOSS",
                "D5_GAIN_GE_20",
                "D5_GAIN_GE_20",
                "D5_LOSS",
                "D5_LOSS",
                "D5_GAIN_GE_20",
                "D5_GAIN_GE_20",
            ],
            "d5_close_date": [
                "2026-01-09",
                "2026-01-12",
                "2026-01-13",
                "2026-01-14",
                "2026-04-08",
                "2026-04-09",
                "2026-04-10",
                "2026-04-13",
            ],
            "feature_x": [0.0, 2.0, 8.0, 10.0, 3.0, 4.0, 9.0, 11.0],
        }
    )

    result = build_univariate_holdout_reference(
        rows,
        features=["feature_x"],
        min_discovery_class_rows=2,
        min_holdout_selected_rows=1,
    )
    row = result[result["task"].eq("D5_GAIN_GE20_VS_LOSS")].iloc[0]

    assert row["direction"] == "HIGHER"
    assert row["threshold"] == pytest.approx(5.0)
    assert row["holdout_selected_rows"] == 2
    assert row["holdout_precision"] == pytest.approx(1.0)
    assert row["holdout_lift"] == pytest.approx(2.0)


def test_univariate_reference_purges_labels_maturing_after_discovery() -> None:
    rows = pd.DataFrame(
        {
            "asof_date": [
                "2026-03-20",
                "2026-03-23",
                "2026-03-24",
                "2026-03-31",
                "2026-04-01",
                "2026-04-02",
            ],
            "d5_close_date": [
                "2026-03-27",
                "2026-03-30",
                "2026-03-31",
                "2026-04-09",
                "2026-04-09",
                "2026-04-10",
            ],
            "d5_group": [
                "D5_LOSS",
                "D5_GAIN_GE_20",
                "D5_GAIN_GE_20",
                "D5_LOSS",
                "D5_LOSS",
                "D5_GAIN_GE_20",
            ],
            "feature_x": [0.0, 8.0, 10.0, 100.0, 2.0, 12.0],
        }
    )

    result = build_univariate_holdout_reference(
        rows,
        features=["feature_x"],
        min_discovery_class_rows=1,
        min_holdout_selected_rows=1,
    )
    row = result[result["task"].eq("D5_GAIN_GE20_VS_LOSS")].iloc[0]

    assert row["threshold"] == pytest.approx(4.5)
    assert row["discovery_label_maturity_purged_rows"] == 1


def test_pairwise_comparison_reports_gain_minus_loss_medians() -> None:
    rows = pd.DataFrame(
        {
            "d5_group": ["D5_LOSS", "D5_LOSS", "D5_GAIN_10_20", "D5_GAIN_10_20"],
            "d5_group_label": ["loss", "loss", "gain", "gain"],
            "pre_foreign_net_volume_ratio_5d_pct": [-2.0, 0.0, 4.0, 6.0],
        }
    )

    result = compare_gain_groups_with_loss(
        rows,
        features=["pre_foreign_net_volume_ratio_5d_pct"],
        scope="test",
    ).iloc[0]

    assert result["target_median"] == pytest.approx(5.0)
    assert result["reference_median"] == pytest.approx(-1.0)
    assert result["median_difference"] == pytest.approx(6.0)


def _price_history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    close = np.linspace(100.0, 120.0, size)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "open": close * 0.995,
            "close": close,
            "volume": np.linspace(1_000_000.0, 1_500_000.0, size),
            "sma20_gap": [0.05] * size,
            "range_pos_20": [0.7] * size,
            "day_volume_ratio_20": [1.2] * size,
            "upper_tail_flag": [0] * size,
            "volume_exhaustion_flag": [0] * size,
            "late_chase_risk_flag": [0] * size,
        }
    )


def _institutional_history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "foreign_net_buy_shares": np.linspace(-10_000.0, 10_000.0, size),
            "trust_net_buy_shares": [1000.0] * size,
            "dealer_net_buy_shares": [500.0] * size,
            "institutional_net_buy_shares": [1500.0] * size,
            "flow_available": [1] * size,
        }
    )


def _holder_history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    return pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330"] * size,
            "holder_source_date": dates,
            "alignment_status": ["ok"] * size,
            "source_kind": ["official"] * size,
            "big_holder_ratio_1000_lots_pct": np.linspace(40.0, 45.0, size),
            "big_holder_count_1000_lots": np.linspace(10.0, 20.0, size),
        }
    )


def _margin_history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    size = len(dates)
    return pd.DataFrame(
        {
            "trade_date": dates,
            "stock_id": ["2330"] * size,
            "margin_balance": np.linspace(1000.0, 1200.0, size),
            "available_date": dates,
        }
    )
