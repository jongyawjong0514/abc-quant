from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from scripts.analyze_zhu_walkline_d10_deep_factors import (
    add_anchor_columns,
    apply_outcome_free_cooldown,
    attach_market_calendar_execution_labels,
    build_factor_manifest,
    build_holdout_bootstrap,
    daily_matched_top_k_with_cooldown,
    select_model_features,
)


def test_daily_matched_top_k_enforces_cooldown_before_filling_quota() -> None:
    dates = pd.bdate_range("2026-05-11", periods=6)
    stocks = [f"{index:04d}" for index in range(1, 7)]
    rows = []
    for trade_index, date in enumerate(dates):
        for stock_rank, stock_id in enumerate(stocks):
            rows.append(
                {
                    "asof_date": date,
                    "stock_id": stock_id,
                    "signal_trade_index": trade_index,
                    "score": 1.0 - stock_rank / 10.0,
                    "reference": stock_rank == trade_index,
                }
            )
    frame = pd.DataFrame(rows)

    selected, audit = daily_matched_top_k_with_cooldown(
        frame,
        score_column="score",
        reference_column="reference",
        minimum_trade_days=5,
    )

    chosen = frame.loc[selected].sort_values("asof_date")
    assert chosen["stock_id"].tolist() == ["0001", "0002", "0003", "0004", "0005", "0001"]
    assert audit["reference_quota"].tolist() == [1] * 6
    assert audit["selected_rows"].tolist() == [1] * 6
    assert audit["quota_shortfall"].sum() == 0
    for _, group in chosen.groupby("stock_id"):
        assert group["signal_trade_index"].diff().dropna().ge(5).all()


def test_holdout_bootstrap_uses_tradable_population_when_configured() -> None:
    rows = pd.DataFrame(
        {
            "split": ["HOLDOUT"] * 8,
            "asof_date": ["2026-05-11"] * 4 + ["2026-05-12"] * 4,
            "target_gain_ge10": [1, 0, 0, 1, 0, 1, 0, 1],
            "net_return_pct": [12.0, -2.0, -3.0, 11.0, -1.0, 13.0, -4.0, 15.0],
            "prob_tech_plus_inst": [0.8, 0.2, 0.1, 0.7, 0.2, 0.8, 0.1, 0.7],
            "prob_tech_base": [0.7, 0.3, 0.2, 0.6, 0.3, 0.7, 0.2, 0.6],
            "prob_prespecified_t1": [0.6, 0.2, 0.2, 0.6, 0.2, 0.6, 0.2, 0.6],
            "tech_plus_inst_matched_t1": [True, False, False, True] * 2,
            "tech_base_matched_t1": [True, False, False, True] * 2,
            "tech_plus_inst_threshold": [True, False, False, True] * 2,
            "tech_base_threshold": [True, False, False, True] * 2,
            "prespecified_t1": [True, False, False, True] * 2,
            "entry_locked_limit_up": [False, True, False, False] + [False] * 4,
        }
    )
    config = {
        "execution": {"exclude_entry_locked_limit_up_from_tradable_view": True},
        "factor_frontier": {"bootstrap_repetitions": 20, "random_seed": 7},
        "analysis": {"tail_loss_net_return_pct": -3.0},
    }

    result = build_holdout_bootstrap(rows, config=config)

    assert set(result["evaluation_rows"]) == {7}
    assert set(result["tail_loss_threshold"]) == {-3.0}
    assert len(result) == 20


def test_execution_labels_use_shared_market_calendar_not_stock_specific_shift() -> None:
    dates = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])
    adjusted = pd.DataFrame(
        [
            (date, stock_id, close)
            for date, close in zip(dates, [100.0, 101.0, 102.0], strict=True)
            for stock_id in ["2330", "2317"]
            if not (stock_id == "2317" and date == dates[-1])
        ],
        columns=["date", "stock_id", "adj_close"],
    )
    adjusted["adj_open"] = adjusted["adj_close"]
    adjusted["adj_high"] = adjusted["adj_close"]
    adjusted["adj_low"] = adjusted["adj_close"]
    adjusted["adj_previous_close"] = adjusted.groupby("stock_id")["adj_close"].shift()
    adjusted["adjustment_factor"] = 1.0
    adjusted["factor_event_count"] = 0
    frame = pd.DataFrame(
        {
            "asof_date": ["2026-01-02", "2026-01-02"],
            "stock_id": ["2330", "2317"],
        }
    )

    result = attach_market_calendar_execution_labels(
        frame,
        adjusted_prices=adjusted,
        horizon_trading_days=2,
        brokerage_fee_rate=0.0,
        sell_tax_rate=0.0,
        one_way_slippage_rate=0.0,
    ).set_index("stock_id")

    assert result.loc["2330", "entry_date"] == "2026-01-05"
    assert result.loc["2330", "exit_date"] == "2026-01-06"
    assert bool(result.loc["2330", "label_mature"])
    assert result.loc["2330", "gross_return_pct"] == pytest.approx(
        (102.0 / 101.0 - 1.0) * 100.0
    )
    assert not bool(result.loc["2317", "label_mature"])


def test_add_anchor_columns_preserves_factor_names_without_merge_suffixes() -> None:
    dates = pd.to_datetime(["2026-01-02", "2026-01-05"])
    factor_panel = pd.DataFrame(
        {
            "observation_date": dates,
            "stock_id": ["2330", "2330"],
            "technical_source_date": dates,
            "volume_ratio_20": [0.6, 0.8],
            "close_to_ma20_pct": [-1.0, 0.5],
        }
    )
    walkline = pd.DataFrame(
        {
            "date": dates,
            "stock_id": ["2330", "2330"],
            "open": [99.0, 100.0],
            "high": [101.0, 103.0],
            "low": [98.0, 99.0],
            "close": [100.0, 102.0],
            "volume": [1_000.0, 1_200.0],
            "return_1d": [np.nan, 0.02],
            "swing_low_1": [98.0, 98.0],
            "amount_ma20": [20_000_000.0, 21_000_000.0],
        }
    )

    result = add_anchor_columns(factor_panel, walkline)

    assert not result.columns.duplicated().any()
    assert not any(column.endswith(("_x", "_y")) for column in result.columns)
    assert result["volume_ratio_20"].tolist() == [0.6, 0.8]
    assert result["close_to_ma20_pct"].tolist() == [-1.0, 0.5]
    assert result["return_1d_pct"].iloc[1] == 2.0
    assert result["history_rows"].tolist() == [1, 2]


def test_outcome_free_cooldown_is_invariant_to_forward_outcome_mutations() -> None:
    rows = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-02",
                    "2026-01-06",
                    "2026-01-07",
                    "2026-01-09",
                    "2026-01-02",
                ]
            ),
            "stock_id": ["2330", "2330", "2330", "2330", "2317"],
            "signal_trade_index": [0, 2, 3, 5, 0],
            "net_return_pct": [12.0, -8.0, 25.0, -3.0, 11.0],
            "target_gain_ge10": [True, False, True, False, True],
            "exit_adj_close": [112.0, 92.0, 125.0, 97.0, 111.0],
        }
    )
    candidate_mask = pd.Series(True, index=rows.index)

    baseline = apply_outcome_free_cooldown(
        rows,
        candidate_mask,
        minimum_trade_days=3,
    )
    mutated = rows.copy()
    mutated["net_return_pct"] = [-999.0, 999.0, -999.0, 999.0, -999.0]
    mutated["target_gain_ge10"] = ~mutated["target_gain_ge10"]
    mutated["exit_adj_close"] = np.nan
    after_outcome_mutation = apply_outcome_free_cooldown(
        mutated,
        candidate_mask,
        minimum_trade_days=3,
    )

    assert baseline.tolist() == [True, False, True, False, True]
    pd.testing.assert_series_equal(baseline, after_outcome_mutation)


def test_model_feature_selection_uses_discovery_coverage_only() -> None:
    rows = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-02",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                    "2026-03-02",
                    "2026-03-03",
                    "2026-03-04",
                    "2026-03-05",
                ]
            ),
            "discovery_covered": [1.0, 2.0, np.nan, 4.0, np.nan, np.nan, np.nan, np.nan],
            "post_discovery_only": [np.nan, np.nan, np.nan, np.nan, 1.0, 2.0, 3.0, 4.0],
            "non_finite_discovery": [np.inf, -np.inf, np.nan, np.nan, 1.0, 2.0, 3.0, 4.0],
            "explicitly_excluded": [1.0] * 8,
        }
    )
    candidates = (
        "discovery_covered",
        "post_discovery_only",
        "non_finite_discovery",
        "explicitly_excluded",
        "missing_column",
    )

    baseline = select_model_features(
        rows,
        candidates=candidates,
        start_date="2026-01-01",
        end_date="2026-02-28",
        minimum_coverage=0.75,
        exclusions={"explicitly_excluded"},
    )
    mutated = rows.copy()
    outside_discovery = mutated["date"].gt(pd.Timestamp("2026-02-28"))
    mutated.loc[outside_discovery, "discovery_covered"] = 999.0
    mutated.loc[outside_discovery, "post_discovery_only"] = np.nan
    mutated.loc[outside_discovery, "non_finite_discovery"] = -999.0
    after_post_discovery_mutation = select_model_features(
        mutated,
        candidates=candidates,
        start_date="2026-01-01",
        end_date="2026-02-28",
        minimum_coverage=0.75,
        exclusions={"explicitly_excluded"},
    )

    assert baseline == ["discovery_covered"]
    assert after_post_discovery_mutation == baseline


def test_factor_manifest_is_stable_and_contains_no_raw_position_features() -> None:
    config = {
        "factor_frontier": {
            "volume_ratio_fixed_thresholds": [0.5, 0.8, 1.0, 1.2],
        },
        "model": {"mutation_id": "d10_technical_plus_institutional_v1"},
    }
    technical_features = ["kd_k9", "volume_ratio_20"]
    institutional_features = [
        "foreign_net_volume_ratio_5d_pct",
        "institutional_total_net_volume_ratio_slope_5d_pctpt",
    ]

    first = build_factor_manifest(
        technical_features=technical_features,
        institutional_features=institutional_features,
        config=config,
    )
    reordered_config = {
        "model": {"mutation_id": "d10_technical_plus_institutional_v1"},
        "unrelated": {"does_not_enter_manifest": True},
        "factor_frontier": {
            "volume_ratio_fixed_thresholds": [0.5, 0.8, 1.0, 1.2],
        },
    }
    second = build_factor_manifest(
        technical_features=copy.copy(technical_features),
        institutional_features=copy.copy(institutional_features),
        config=reordered_config,
    )

    exported_features = [
        *first["technical_features"],
        *first["institutional_features"],
    ]
    assert not any("shares" in feature.lower() for feature in exported_features)
    assert not any("balance" in feature.lower() for feature in exported_features)
    assert first["raw_institutional_shares_exported"] is False
    assert first["raw_margin_balance_exported"] is False
    assert first["sha256"] == second["sha256"]
    assert first == second
