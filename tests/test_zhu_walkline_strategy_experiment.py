from __future__ import annotations

import pandas as pd
import pytest

from scripts.experiment_zhu_walkline_strategy import (
    BASELINE_VARIANT,
    EVALUATION_SCOPE,
    _evaluation_scopes,
    apply_signal_cooldown,
    assign_temporal_split,
    attach_execution_labels,
    build_variant_masks,
    compute_failure_attribution,
    derive_post_holdout_research_recommendations,
    load_candidate_files,
    review_prespecified_replications,
    select_variant_from_validation,
)


def test_execution_labels_use_next_open_d20_close_costs_and_adjustment_flag() -> None:
    frame = pd.DataFrame(
        {
            "asof_date": ["2025-01-02"],
            "stock_id": ["1234"],
        }
    )
    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
            "stock_id": ["1234", "1234", "1234"],
            "adj_open": [99.0, 102.0, 108.0],
            "adj_close": [100.0, 104.0, 110.0],
            "adjustment_factor": [0.9, 0.9, 1.0],
            "factor_event_count": [1, 1, 0],
        }
    )

    labeled = attach_execution_labels(
        frame,
        adjusted_prices=prices,
        horizon_trading_days=2,
        brokerage_fee_rate=0.001425,
        sell_tax_rate=0.003,
        one_way_slippage_rate=0.001,
    )

    row = labeled.iloc[0]
    expected_net = (
        (110.0 * (1.0 - 0.001425 - 0.003 - 0.001))
        / (102.0 * (1.0 + 0.001425 + 0.001))
        - 1.0
    ) * 100.0
    assert row["entry_date"] == "2025-01-03"
    assert row["exit_date"] == "2025-01-06"
    assert row["entry_adj_open"] == 102.0
    assert row["exit_adj_close"] == 110.0
    assert row["gross_return_pct"] == pytest.approx((110.0 / 102.0 - 1.0) * 100.0)
    assert row["net_return_pct"] == pytest.approx(expected_net)
    assert bool(row["corporate_action_event_in_horizon"]) is True
    assert bool(row["entry_locked_limit_up"]) is False
    assert bool(row["label_mature"]) is True


@pytest.mark.parametrize(
    ("entry_high", "entry_low", "expected_locked"),
    [(110.0, 110.0, True), (111.0, 109.0, False)],
)
def test_entry_locked_limit_up_requires_limit_return_and_one_price_range(
    entry_high: float,
    entry_low: float,
    expected_locked: bool,
) -> None:
    frame = pd.DataFrame({"asof_date": ["2025-01-02"], "stock_id": ["1234"]})
    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
            "stock_id": ["1234", "1234", "1234"],
            "adj_open": [100.0, 110.0, 112.0],
            "adj_high": [101.0, entry_high, 113.0],
            "adj_low": [99.0, entry_low, 111.0],
            "adj_close": [100.0, 110.0, 112.0],
            "adj_previous_close": [99.0, 100.0, 110.0],
            "adjustment_factor": [1.0, 1.0, 1.0],
            "factor_event_count": [0, 0, 0],
        }
    )

    row = attach_execution_labels(
        frame,
        adjusted_prices=prices,
        horizon_trading_days=2,
        brokerage_fee_rate=0.001425,
        sell_tax_rate=0.003,
        one_way_slippage_rate=0.001,
    ).iloc[0]

    assert row["entry_return_vs_previous_close_pct"] == pytest.approx(10.0)
    assert bool(row["entry_locked_limit_up"]) is expected_locked


def test_buyable_scope_excludes_locked_limit_up_without_changing_primary_scope() -> None:
    trading_dates = pd.bdate_range("2025-01-02", periods=3).strftime("%Y-%m-%d").tolist()
    frame = pd.DataFrame(
        {
            "asof_date": [trading_dates[0], trading_dates[0]],
            "stock_id": ["1234", "5678"],
            "driver_score": [11.0, 11.0],
            "corporate_action_event_in_horizon": [False, False],
            "entry_locked_limit_up": [True, False],
        }
    )

    scopes = _evaluation_scopes(
        frame,
        trading_dates=trading_dates,
        horizon_trading_days=20,
    )

    assert len(scopes[EVALUATION_SCOPE]) == 2
    assert scopes["cooldown_20d_buyable_entry"]["stock_id"].tolist() == ["5678"]


def test_future_evaluator_values_do_not_change_variant_membership() -> None:
    base = pd.DataFrame(
        {
            "driver_score": [11.0],
            "late_chase_risk_flag": [0],
            "upper_tail_flag": [0],
            "volume_exhaustion_flag": [0],
            "close_to_sma5_pct": [8.0],
            "avg_turnover_20_ntd": [30_000_000.0],
            "sector_neutral_driver_score": [8.0],
            "net_return_pct": [25.0],
            "exit_adj_close": [125.0],
            "entry_adj_high": [110.0],
            "entry_adj_low": [110.0],
            "entry_adj_previous_close": [100.0],
            "entry_locked_limit_up": [True],
        }
    )
    changed_future = base.copy()
    changed_future["net_return_pct"] = -50.0
    changed_future["exit_adj_close"] = 50.0
    changed_future["entry_adj_high"] = 95.0
    changed_future["entry_adj_low"] = 90.0
    changed_future["entry_adj_previous_close"] = 120.0
    changed_future["entry_locked_limit_up"] = False

    before = build_variant_masks(base)
    after = build_variant_masks(changed_future)

    assert before.keys() == after.keys()
    for variant in before:
        assert before[variant].tolist() == after[variant].tolist()


def test_market_regime_variant_excludes_strong_uptrend_and_requires_known_state() -> None:
    frame = pd.DataFrame(
        {
            "driver_score": [11.0, 11.0, 11.0],
            "late_chase_risk_flag": [0, 0, 0],
            "upper_tail_flag": [0, 0, 0],
            "volume_exhaustion_flag": [0, 0, 0],
            "close_to_sma5_pct": [8.0, 8.0, 8.0],
            "avg_turnover_20_ntd": [30_000_000.0] * 3,
            "sector_neutral_driver_score": [8.0, 8.0, 8.0],
            "market_state": ["MARKET_STRONG_UPTREND", "MARKET_RANGE_BOUND", pd.NA],
        }
    )

    masks = build_variant_masks(frame)

    assert masks["BASELINE_EXCLUDE_STRONG_UPTREND"].tolist() == [False, True, False]


def test_missing_risk_flags_fail_clean_guard_without_nan_strings() -> None:
    frame = pd.DataFrame(
        {
            "driver_score": [11.0],
            "late_chase_risk_flag": [pd.NA],
            "upper_tail_flag": [pd.NA],
            "volume_exhaustion_flag": [pd.NA],
            "close_to_sma5_pct": [pd.NA],
            "avg_turnover_20_ntd": [pd.NA],
            "sector_neutral_driver_score": [8.0],
        }
    )

    masks = build_variant_masks(frame)

    assert bool(masks[BASELINE_VARIANT].iloc[0]) is True
    assert bool(masks["BALANCED_RISK_GUARD"].iloc[0]) is False
    assert all("nan" not in str(value).lower() for value in masks.values())


def test_holdout_values_cannot_change_validation_only_variant_selection() -> None:
    metrics = _selection_metrics(holdout_mutation_return=12.0)
    changed_holdout = _selection_metrics(holdout_mutation_return=-99.0)

    first = select_variant_from_validation(
        metrics,
        minimum_validation_rows=50,
        minimum_validation_coverage=0.30,
    )
    second = select_variant_from_validation(
        changed_holdout,
        minimum_validation_rows=50,
        minimum_validation_coverage=0.30,
    )

    assert first["selected_variant"] == "SCORE_12"
    assert second["selected_variant"] == "SCORE_12"
    assert first["holdout_used"] is False
    assert second["holdout_used"] is False


def test_validation_selection_rejects_no_effect_mutation() -> None:
    metrics = _selection_metrics(holdout_mutation_return=12.0)
    baseline_validation = metrics[
        metrics["variant"].eq(BASELINE_VARIANT)
        & metrics["split"].eq("validation")
    ].iloc[0].to_dict()
    no_effect = {
        **baseline_validation,
        "variant": "BASELINE_NO_LATE_CHASE",
        "cohort_type": "mutation",
    }
    metrics = pd.concat([metrics, pd.DataFrame([no_effect])], ignore_index=True)

    selection = select_variant_from_validation(
        metrics[~metrics["variant"].eq("SCORE_12")],
        minimum_validation_rows=50,
        minimum_validation_coverage=0.30,
    )

    assert selection["selected_variant"] == BASELINE_VARIANT
    review = selection["candidate_reviews"][0]
    assert review["no_effect_vs_baseline"] is True
    assert review["pass_validation_gate"] is False


def test_post_holdout_risk_candidate_is_labeled_as_research_only() -> None:
    metrics = pd.DataFrame(
        [
            _risk_metric(BASELINE_VARIANT, "baseline", "validation", 100, 5.0, 1.0, 0.20),
            _risk_metric(BASELINE_VARIANT, "baseline", "holdout", 100, 10.0, 3.0, 0.21),
            _risk_metric(
                "BASELINE_MA5_GAP_CAP_12",
                "mutation",
                "validation",
                90,
                5.2,
                1.2,
                0.18,
            ),
            _risk_metric(
                "BASELINE_MA5_GAP_CAP_12",
                "mutation",
                "holdout",
                85,
                9.9,
                3.5,
                0.19,
            ),
        ]
    )

    recommendation = derive_post_holdout_research_recommendations(metrics)

    assert recommendation["risk_control_candidate"] == "BASELINE_MA5_GAP_CAP_12"
    assert recommendation["post_holdout_only"] is True
    assert recommendation["not_eligible_for_current_selection"] is True


def test_prespecified_replication_requires_both_splits_and_buyable_scope() -> None:
    rows: list[dict[str, object]] = []
    for scope in [EVALUATION_SCOPE, "cooldown_20d_buyable_entry"]:
        for split in ["validation", "holdout"]:
            rows.extend(
                [
                    {
                        "variant": BASELINE_VARIANT,
                        "evaluation_scope": scope,
                        "split": split,
                        "rows": 100,
                        "avg_net_return_pct": 2.0,
                        "median_net_return_pct": -2.0,
                        "tail_loss_rate_net_le_neg10": 0.20,
                        "downside_rate_net_lt_0": 0.55,
                    },
                    {
                        "variant": "BASELINE_MA5_GAP_CAP_12",
                        "evaluation_scope": scope,
                        "split": split,
                        "rows": 90,
                        "avg_net_return_pct": 1.8,
                        "median_net_return_pct": -1.5,
                        "tail_loss_rate_net_le_neg10": 0.18,
                        "downside_rate_net_lt_0": 0.53,
                    },
                    {
                        "variant": "BASELINE_EXCLUDE_STRONG_UPTREND",
                        "evaluation_scope": scope,
                        "split": split,
                        "rows": 40,
                        "avg_net_return_pct": 3.0,
                        "median_net_return_pct": -1.0,
                        "tail_loss_rate_net_le_neg10": 0.15,
                        "downside_rate_net_lt_0": 0.50,
                    },
                ]
            )

    review = review_prespecified_replications(
        pd.DataFrame(rows),
        variants=[
            "BASELINE_MA5_GAP_CAP_12",
            "BASELINE_EXCLUDE_STRONG_UPTREND",
        ],
    )

    by_variant = {row["variant"]: row for row in review["variant_reviews"]}
    assert by_variant["BASELINE_MA5_GAP_CAP_12"]["replication_supported"] is True
    assert (
        by_variant["BASELINE_EXCLUDE_STRONG_UPTREND"]["replication_supported"]
        is False
    )
    assert review["formal_promotion_eligible"] is False


def test_signal_cooldown_removes_overlapping_same_stock_signals() -> None:
    trading_dates = pd.bdate_range("2025-01-02", periods=25).strftime("%Y-%m-%d").tolist()
    frame = pd.DataFrame(
        {
            "asof_date": [trading_dates[0], trading_dates[1], trading_dates[21]],
            "stock_id": ["1234", "1234", "1234"],
            "driver_score": [11.0, 12.0, 11.0],
        }
    )

    kept = apply_signal_cooldown(
        frame,
        trading_dates=trading_dates,
        cooldown_trading_days=20,
    )

    assert kept["asof_date"].tolist() == [trading_dates[0], trading_dates[21]]


def test_failure_attribution_separates_signal_and_entry_time_features() -> None:
    trading_dates = pd.bdate_range("2025-01-02", periods=3).strftime("%Y-%m-%d").tolist()
    frame = pd.DataFrame(
        {
            "asof_date": [trading_dates[0], trading_dates[1]],
            "stock_id": ["1234", "5678"],
            "driver_score": [11.0, 12.0],
            "market_state": ["MARKET_RANGE_BOUND", "MARKET_STRONG_UPTREND"],
            "sector_state": ["SECTOR_LEADING", "SECTOR_ROTATING_IN"],
            "split": ["validation", "validation"],
            "gross_return_pct": [10.0, -12.0],
            "net_return_pct": [9.0, -13.0],
            "entry_gap_pct": [1.0, 6.0],
            "close_to_sma5_pct": [6.0, 13.0],
            "corporate_action_event_in_horizon": [False, False],
            "avg_turnover_20_ntd": [30_000_000.0, 40_000_000.0],
        }
    )

    attribution = compute_failure_attribution(
        frame,
        trading_dates=trading_dates,
        horizon_trading_days=20,
    )

    entry_rows = attribution[attribution["dimension"].eq("entry_gap_bucket")]
    signal_rows = attribution[attribution["dimension"].eq("ma5_gap_bucket")]
    assert set(entry_rows["feature_timing"]) == {"entry_time"}
    assert set(signal_rows["feature_timing"]) == {"signal_time"}
    assert not attribution["bucket"].astype(str).str.lower().eq("nan").any()


def test_temporal_split_rejects_overlap_and_assigns_boundaries() -> None:
    frame = pd.DataFrame(
        {
            "asof_date": ["2024-12-31", "2025-12-31", "2026-06-10"],
        }
    )

    split = assign_temporal_split(
        frame,
        development_end="2024-12-31",
        validation_end="2025-12-31",
        holdout_end="2026-06-10",
    )

    assert split["split"].tolist() == ["development", "validation", "holdout"]
    with pytest.raises(ValueError, match="development < validation < holdout"):
        assign_temporal_split(
            frame,
            development_end="2025-12-31",
            validation_end="2024-12-31",
            holdout_end="2026-06-10",
        )


def test_candidate_files_append_and_deduplicate(tmp_path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    pd.DataFrame(
        {
            "asof_date": ["2024-01-02"],
            "stock_id": ["1234"],
            "early_observation_rule": ["STRICT_BREAKOUT"],
            "close": [10.0],
        }
    ).to_csv(first, index=False)
    pd.DataFrame(
        {
            "asof_date": ["2024-01-02", "2025-01-02"],
            "stock_id": ["1234", "5678"],
            "early_observation_rule": ["STRICT_BREAKOUT", "STRICT_SUPPORT_TURN"],
            "close": [10.5, 20.0],
        }
    ).to_csv(second, index=False)

    combined = load_candidate_files([first, second])

    assert len(combined) == 2
    assert combined["stock_id"].tolist() == ["1234", "5678"]
    assert combined.iloc[0]["close"] == 10.5


def _selection_metrics(*, holdout_mutation_return: float) -> pd.DataFrame:
    common = {
        "evaluation_scope": EVALUATION_SCOPE,
        "rows": 100,
        "hit_rate_net_ge_20": 0.25,
    }
    return pd.DataFrame(
        [
            {
                **common,
                "variant": BASELINE_VARIANT,
                "cohort_type": "baseline",
                "split": "validation",
                "avg_net_return_pct": 8.0,
                "median_net_return_pct": 4.0,
                "tail_loss_rate_net_le_neg10": 0.20,
                "downside_rate_net_lt_0": 0.40,
            },
            {
                **common,
                "variant": "SCORE_12",
                "cohort_type": "mutation",
                "split": "validation",
                "avg_net_return_pct": 10.0,
                "median_net_return_pct": 5.0,
                "tail_loss_rate_net_le_neg10": 0.18,
                "downside_rate_net_lt_0": 0.35,
            },
            {
                **common,
                "variant": BASELINE_VARIANT,
                "cohort_type": "baseline",
                "split": "holdout",
                "avg_net_return_pct": 9.0,
                "median_net_return_pct": 4.5,
                "tail_loss_rate_net_le_neg10": 0.19,
                "downside_rate_net_lt_0": 0.38,
            },
            {
                **common,
                "variant": "SCORE_12",
                "cohort_type": "mutation",
                "split": "holdout",
                "avg_net_return_pct": holdout_mutation_return,
                "median_net_return_pct": holdout_mutation_return,
                "tail_loss_rate_net_le_neg10": 0.15,
                "downside_rate_net_lt_0": 0.30,
            },
        ]
    )


def _risk_metric(
    variant: str,
    cohort_type: str,
    split: str,
    rows: int,
    average: float,
    median: float,
    tail: float,
) -> dict[str, object]:
    return {
        "variant": variant,
        "cohort_type": cohort_type,
        "evaluation_scope": EVALUATION_SCOPE,
        "split": split,
        "rows": rows,
        "avg_net_return_pct": average,
        "median_net_return_pct": median,
        "tail_loss_rate_net_le_neg10": tail,
        "downside_rate_net_lt_0": 0.40,
    }
