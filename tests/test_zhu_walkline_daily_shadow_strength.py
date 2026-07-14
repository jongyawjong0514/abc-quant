from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from scripts.run_zhu_walkline_shadow import (
    _assert_explicit_asof_available,
    _early_lowpoint_report_enabled,
    _shadow_strength_report_enabled,
)
from scripts.score_zhu_walkline_daily_shadow_strength import (
    TRAJECTORY_EXPORT_COLUMNS,
    assert_signal_day_score_consistency,
    build_candidate_observation_keys,
    build_scored_candidate_trajectory,
    load_frozen_rules,
    render_markdown,
    select_daily_confirmation_candidates,
)
from abc_quant.features.shadow_strength import ShadowStrengthRule


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_daily_candidate_selection_requires_same_day_confirmation() -> None:
    rows = pd.DataFrame(
        {
            "asof_date": ["2026-07-13"] * 4,
            "trade_date": [
                "2026-07-13",
                "2026-07-10",
                "2026-07-13",
                "2026-07-13",
            ],
            "stock_id": ["1434", "6517", "6944", "9921"],
            "stock_name": ["A", "B", "C", "D"],
            "kd_recovery_confirmation": [True, True, False, "true"],
        }
    )

    selected = select_daily_confirmation_candidates(rows, asof_date="2026-07-13")

    assert selected["stock_id"].tolist() == ["1434", "9921"]


def test_frozen_daily_rules_require_exact_four_components(tmp_path) -> None:
    rules = pd.DataFrame(
        [
            _rule("main_force", "pre_main_force_net_lots_1d"),
            _rule("no_upper_tail", "pre5_upper_tail_count"),
            _rule("volume_ratio", "pre_day_volume_ratio_20"),
        ]
    )
    path = tmp_path / "rules.csv"
    rules.to_csv(path, index=False)

    with pytest.raises(ValueError, match="exactly the frozen four"):
        load_frozen_rules(path)


def test_pullback_market_report_uses_promotion_reason_for_watch_only() -> None:
    report = render_markdown(
        {
            "as_of": "2026-06-02",
            "market_state": "MARKET_PULLBACK_IN_UPTREND",
            "market_score": 6,
            "market_risk_score": 4,
            "candidate_rows": 0,
            "complete_score_rows": 0,
            "ranked_rows": [],
        }
    )

    assert "尚未通過正式 promotion review" in report
    assert "市場風險 gate 未解除" not in report


def test_tracked_four_component_rules_are_the_default_contract() -> None:
    rules = load_frozen_rules(
        REPO_ROOT / "config" / "zhu_walkline_shadow_strength_rules.csv"
    )

    assert [rule.component for rule in rules] == [
        "main_force",
        "no_upper_tail",
        "volume_ratio",
        "margin_change",
    ]
    assert sum(rule.points for rule in rules) == 100
    assert "pre_margin_balance" not in {rule.feature for rule in rules}
    assert not any("foreign" in rule.feature for rule in rules)


def test_daily_scanner_enables_strength_report_unless_explicitly_skipped() -> None:
    config = {"shadow_strength_report": {"enabled": True}}

    assert _shadow_strength_report_enabled(config, skip=False)
    assert not _shadow_strength_report_enabled(config, skip=True)
    assert not _shadow_strength_report_enabled(
        {"shadow_strength_report": {"enabled": False}}, skip=False
    )


def test_daily_scanner_enables_early_lowpoint_unless_explicitly_skipped() -> None:
    config = {"early_lowpoint_report": {"enabled": True}}

    assert _early_lowpoint_report_enabled(config, skip=False)
    assert not _early_lowpoint_report_enabled(config, skip=True)
    assert not _early_lowpoint_report_enabled(
        {"early_lowpoint_report": {"enabled": False}}, skip=False
    )


def test_explicit_asof_requires_exact_date_in_both_price_tables(tmp_path) -> None:
    sqlite_path = tmp_path / "market.sqlite"
    with sqlite3.connect(sqlite_path) as connection:
        for table in ("daily_ohlcv_features", "tw_adjusted_ohlcv_daily"):
            connection.execute(
                f"CREATE TABLE {table} (date TEXT NOT NULL, stock_id TEXT NOT NULL)"
            )
            connection.execute(
                f"INSERT INTO {table} (date, stock_id) VALUES (?, ?)",
                ("2026-07-14", "2464"),
            )
    config = {"data": {"sqlite_path": str(sqlite_path)}}

    _assert_explicit_asof_available(config, "2026-07-14")
    _assert_explicit_asof_available(config, "2026-07-14", stock_id="2464")


def test_explicit_asof_fails_closed_when_any_required_price_table_is_missing_date(
    tmp_path,
) -> None:
    sqlite_path = tmp_path / "market.sqlite"
    with sqlite3.connect(sqlite_path) as connection:
        for table in ("daily_ohlcv_features", "tw_adjusted_ohlcv_daily"):
            connection.execute(
                f"CREATE TABLE {table} (date TEXT NOT NULL, stock_id TEXT NOT NULL)"
            )
        connection.execute(
            "INSERT INTO daily_ohlcv_features (date, stock_id) VALUES (?, ?)",
            ("2026-07-14", "2464"),
        )
    config = {"data": {"sqlite_path": str(sqlite_path)}}

    with pytest.raises(RuntimeError, match="refusing to fall back"):
        _assert_explicit_asof_available(config, "2026-07-14")


def test_latest_asof_bypasses_exact_date_gate() -> None:
    _assert_explicit_asof_available({}, "latest")


def test_candidate_observation_keys_use_stock_trading_days_d10_through_d() -> None:
    dates = pd.bdate_range(end="2026-07-10", periods=10)
    price = pd.DataFrame({"date": dates, "stock_id": "2464"})
    candidates = pd.DataFrame(
        {
            "asof_date": ["2026-07-13"],
            "stock_id": ["2464"],
            "stock_name": ["盟立"],
        }
    )

    rows = build_candidate_observation_keys(candidates, price)

    assert rows["relative_day"].tolist() == [
        "D-10",
        "D-9",
        "D-8",
        "D-7",
        "D-6",
        "D-5",
        "D-4",
        "D-3",
        "D-2",
        "D-1",
        "D",
    ]
    assert rows["asof_date"].iloc[-1] == "2026-07-13"
    assert rows["trajectory_history_status"].eq("COMPLETE").all()


def test_candidate_observation_keys_do_not_invent_missing_history() -> None:
    price = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-08", "2026-07-09", "2026-07-10"]),
            "stock_id": "7777",
        }
    )
    candidates = pd.DataFrame(
        {
            "asof_date": ["2026-07-13"],
            "stock_id": ["7777"],
            "stock_name": ["NEW"],
        }
    )

    rows = build_candidate_observation_keys(candidates, price)

    assert rows["relative_day"].tolist() == ["D-3", "D-2", "D-1", "D"]
    assert rows["trajectory_history_status"].eq("INSUFFICIENT_HISTORY").all()
    assert rows["trajectory_available_prior_days"].eq(3).all()


def test_scored_trajectory_withholds_historical_rank_and_exports_only_four_contract() -> None:
    dates = pd.bdate_range(end="2026-07-10", periods=40)
    price = pd.DataFrame(
        {
            "date": dates,
            "stock_id": "2464",
            "open": 100.0,
            "close": 101.0,
            "volume": 1000.0,
            "sma20_gap": 0.01,
            "range_pos_20": 0.5,
            "day_volume_ratio_20": 0.8,
            "upper_tail_flag": 0,
            "volume_exhaustion_flag": 0,
            "late_chase_risk_flag": 0,
        }
    )
    margin = pd.DataFrame(
        {
            "trade_date": dates,
            "available_date": dates,
            "stock_id": "2464",
            "margin_balance": range(100, 140),
        }
    )
    main_force = pd.DataFrame({"2464": 10.0}, index=dates)
    candidates = pd.DataFrame(
        {
            "asof_date": ["2026-07-13"],
            "stock_id": ["2464"],
            "stock_name": ["盟立"],
        }
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

    rows = build_scored_candidate_trajectory(
        candidates,
        market_calendar=dates,
        price_history=price,
        institutional_history=pd.DataFrame(),
        holder_history=pd.DataFrame(),
        margin_history=margin,
        main_force_panel=main_force,
        broker_count_panel=pd.DataFrame(),
        rules=rules,
    )

    assert len(rows) == 11
    assert rows.loc[rows["lead_days"].gt(0), "shadow_strength_rank_within_signal_date"].isna().all()
    assert rows.loc[rows["lead_days"].eq(0), "shadow_strength_rank_within_signal_date"].eq(1.0).all()
    assert "pre_margin_balance" not in TRAJECTORY_EXPORT_COLUMNS
    assert not any("foreign" in column for column in TRAJECTORY_EXPORT_COLUMNS)
    signal_day = rows[rows["lead_days"].eq(0)].copy()
    assert_signal_day_score_consistency(signal_day, rows)
    signal_day.loc[:, "shadow_strength_score"] = 0.0
    with pytest.raises(AssertionError):
        assert_signal_day_score_consistency(signal_day, rows)


def test_markdown_labels_trajectory_as_retrospective_not_live() -> None:
    report = render_markdown(
        {
            "as_of": "2026-07-13",
            "market_state": "MARKET_PULLBACK_IN_UPTREND",
            "market_score": 6,
            "market_risk_score": 4,
            "candidate_rows": 0,
            "complete_score_rows": 0,
            "ranked_rows": [],
            "trajectory_observations": [],
        }
    )

    assert "D-10～D 四項影子軌跡" in report
    assert "retrospective_confirmed_candidates" in report
    assert "trajectory_live_deployable=False" in report


def _rule(component: str, feature: str) -> dict[str, object]:
    return {
        "component": component,
        "feature": feature,
        "source_date_column": "pre_price_source_date",
        "direction": "HIGHER",
        "threshold": 0.0,
        "points": 25,
        "reference_task": "D5_GAIN_GE10_VS_LOSS",
        "discovery_end": "2026-03-31",
    }
