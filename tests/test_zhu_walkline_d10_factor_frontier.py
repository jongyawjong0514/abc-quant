import numpy as np
import pandas as pd

from abc_quant.validation.d10_factor_frontier import (
    D10FixedRule,
    assign_label_maturity_purged_splits,
    benjamini_hochberg,
    build_factor_permutation_frontier,
    d10_fixed_rule_mask,
    evaluate_frozen_factor_thresholds,
    prespecified_t1_mask,
)


def test_prespecified_t1_uses_only_stock_trading_rows_before_current_row() -> None:
    rows = pd.DataFrame(
        {
            "observation_date": pd.bdate_range("2026-01-01", periods=6),
            "stock_id": "2330",
            "volume_ratio_20": [0.70, 2.0, 2.0, 2.0, 0.80, 0.80],
            "return_1d_pct": [-1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            "future_return": [999.0] * 6,
        }
    )

    baseline = prespecified_t1_mask(
        rows,
        max_t5_volume_ratio_20=0.75,
        min_t3_daily_return_pct=0.0,
        min_t1_daily_return_pct=0.0,
        min_t1_volume_ratio_20=0.70,
    )
    rows["future_return"] = -999.0
    changed = prespecified_t1_mask(
        rows,
        max_t5_volume_ratio_20=0.75,
        min_t3_daily_return_pct=0.0,
        min_t1_daily_return_pct=0.0,
        min_t1_volume_ratio_20=0.70,
    )

    assert baseline.tolist() == [False, False, False, False, True, False]
    pd.testing.assert_series_equal(baseline, changed)


def test_d10_fixed_mask_ignores_outcome_columns() -> None:
    rows = pd.DataFrame(
        {
            "kd_k9": [19.0, 21.0],
            "kd_k_change_1d": [3.0, 3.0],
            "return_1d_pct": [1.5, 1.5],
            "volume_ratio_20": [0.7, 0.7],
            "close_to_ma20_pct": [-1.0, -1.0],
            "distance_from_trailing_5d_low_pct": [4.0, 4.0],
            "net_return_pct": [20.0, -20.0],
        }
    )
    rule = D10FixedRule(20, 2, 1, 0.8, 0, 8)
    baseline = d10_fixed_rule_mask(rows, rule)
    rows["net_return_pct"] *= -100

    changed = d10_fixed_rule_mask(rows, rule)

    assert baseline.tolist() == [True, False]
    pd.testing.assert_series_equal(baseline, changed)


def test_split_assignment_purges_until_prior_labels_are_mature() -> None:
    rows = pd.DataFrame(
        {
            "asof_date": [
                "2026-02-27",
                "2026-03-02",
                "2026-03-09",
                "2026-03-31",
                "2026-04-01",
                "2026-04-10",
                "2026-04-30",
                "2026-05-01",
                "2026-05-15",
            ],
            "exit_date": [
                "2026-03-06",
                "2026-03-09",
                "2026-03-16",
                "2026-04-08",
                "2026-04-10",
                "2026-04-17",
                "2026-05-08",
                "2026-05-08",
                "2026-05-22",
            ],
        }
    )
    windows = {
        "DISCOVERY": ("2026-01-01", "2026-02-28"),
        "VALIDATION": ("2026-03-01", "2026-03-31"),
        "CALIBRATION": ("2026-04-01", "2026-04-30"),
        "HOLDOUT": ("2026-05-01", "2026-06-30"),
    }

    split, audit = assign_label_maturity_purged_splits(rows, windows=windows)

    assert split.tolist() == [
        "DISCOVERY",
        "PURGED",
        "VALIDATION",
        "VALIDATION",
        "PURGED",
        "CALIBRATION",
        "CALIBRATION",
        "PURGED",
        "HOLDOUT",
    ]
    assert audit.set_index("split").loc["VALIDATION", "prior_label_freeze_date"] == (
        "2026-03-06"
    )


def test_factor_frontier_freezes_discovery_threshold_before_other_splits() -> None:
    discovery = pd.DataFrame(
        {
            "asof_date": ["2026-01-02"] * 20 + ["2026-01-05"] * 20,
            "factor": np.arange(40, dtype=float),
            "target": [0] * 10 + [1] * 10 + [0] * 10 + [1] * 10,
            "net_return_pct": [-2.0] * 10 + [12.0] * 10 + [-2.0] * 10 + [12.0] * 10,
        }
    )
    frontier = build_factor_permutation_frontier(
        discovery,
        feature_columns=["factor"],
        target_column="target",
        return_column="net_return_pct",
        date_column="asof_date",
        repetitions=20,
        random_seed=7,
        minimum_coverage=0.8,
    )
    threshold = float(frontier.iloc[0]["threshold"])
    validation = discovery.copy()
    validation["split"] = "VALIDATION"
    validation["factor"] += 1000.0

    evaluated = evaluate_frozen_factor_thresholds(
        validation,
        frontier,
        split_column="split",
        target_column="target",
        return_column="net_return_pct",
    )

    assert float(evaluated.iloc[0]["threshold"]) == threshold
    assert evaluated.iloc[0]["selected_rows"] == len(validation)


def test_benjamini_hochberg_is_monotone_in_ranked_p_values() -> None:
    p_values = np.array([0.04, 0.001, 0.02, 0.50])
    q_values = benjamini_hochberg(p_values)
    ordered = q_values[np.argsort(p_values)]

    assert np.all(np.diff(ordered) >= -1e-12)
    assert np.all((q_values >= 0.0) & (q_values <= 1.0))
