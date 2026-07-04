from abc_quant.pipeline.modeling import run_baseline_modeling_smoke
from abc_quant.pipeline.smoke import SMOKE_FEATURE_COLUMNS, SMOKE_LABEL_COLUMN


EVALUATION_METRIC_KEYS = {
    "split_name",
    "row_count",
    "non_missing_count",
    "missing_actual_count",
    "mae",
    "rmse",
    "mean_error",
    "prediction_mean",
}


def test_baseline_modeling_smoke_summary_is_deterministic() -> None:
    first = run_baseline_modeling_smoke()
    second = run_baseline_modeling_smoke()

    assert first == second


def test_baseline_modeling_smoke_summary_contains_expected_contract() -> None:
    summary = run_baseline_modeling_smoke()

    assert set(summary) == {
        "row_count",
        "ticker_count",
        "rows_per_ticker",
        "feature_columns",
        "label_column",
        "label_non_missing_count",
        "label_missing_count",
        "split_counts",
        "fitted_value",
        "training_label_count",
        "evaluation",
    }
    assert summary["row_count"] == 24
    assert summary["ticker_count"] == 2
    assert summary["rows_per_ticker"] == {"2317": 12, "2330": 12}
    assert summary["split_counts"] == {"train": 8, "validation": 6, "test": 10}
    assert summary["training_label_count"] == 8
    assert summary["label_non_missing_count"] == 18
    assert summary["label_missing_count"] == 6

    evaluation = summary["evaluation"]
    assert set(evaluation) == {"train", "validation", "test"}
    for split_name, metrics in evaluation.items():
        assert set(metrics) == EVALUATION_METRIC_KEYS
        assert metrics["split_name"] == split_name

    assert evaluation["train"]["row_count"] == 8
    assert evaluation["validation"]["row_count"] == 6
    assert evaluation["test"]["row_count"] == 10
    assert evaluation["test"]["missing_actual_count"] == 6


def test_baseline_modeling_smoke_keeps_label_out_of_features() -> None:
    summary = run_baseline_modeling_smoke()

    assert summary["feature_columns"] == SMOKE_FEATURE_COLUMNS
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert SMOKE_LABEL_COLUMN not in summary["feature_columns"]


def test_baseline_modeling_smoke_does_not_expose_market_action_or_simulation_keys() -> None:
    summary = run_baseline_modeling_smoke()
    forbidden_keys = {
        "signals",
        "trading_signals",
        "positions",
        "portfolio",
        "portfolio_values",
        "allocations",
        "equity_curve",
        "performance_curve",
        "backtest",
        "backtest_results",
        "simulation",
        "simulation_results",
    }

    assert forbidden_keys.isdisjoint(_all_dict_keys(summary))


def _all_dict_keys(value: object) -> set[str]:
    if not isinstance(value, dict):
        return set()

    keys = {str(key) for key in value}
    nested_keys: set[str] = set()
    for nested in value.values():
        nested_keys.update(_all_dict_keys(nested))
    return keys | nested_keys
