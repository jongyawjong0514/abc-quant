import pandas as pd

from abc_quant.pipeline.smoke import (
    SMOKE_FEATURE_COLUMNS,
    SMOKE_LABEL_COLUMN,
    SMOKE_METRIC_KEYS,
    build_smoke_frame,
    run_smoke_pipeline,
)


def test_smoke_pipeline_summary_contains_expected_contract_keys() -> None:
    summary = run_smoke_pipeline()

    assert set(summary) == {
        "row_count",
        "ticker_count",
        "rows_per_ticker",
        "feature_columns",
        "label_column",
        "label_non_null_count",
        "metric_keys",
        "metrics",
        "first_momentum_is_null_by_ticker",
    }
    assert summary["row_count"] == 24
    assert summary["ticker_count"] == 2
    assert summary["rows_per_ticker"] == {"2317": 12, "2330": 12}
    assert summary["feature_columns"] == SMOKE_FEATURE_COLUMNS
    assert summary["label_column"] == SMOKE_LABEL_COLUMN
    assert summary["metric_keys"] == SMOKE_METRIC_KEYS
    assert set(summary["metrics"]) == set(SMOKE_METRIC_KEYS)
    assert summary["label_non_null_count"] == 18


def test_smoke_frame_has_features_label_and_ticker_isolation() -> None:
    frame = build_smoke_frame()

    assert set(SMOKE_FEATURE_COLUMNS).issubset(frame.columns)
    assert SMOKE_LABEL_COLUMN in frame.columns
    assert frame.groupby("ticker").size().to_dict() == {"2317": 12, "2330": 12}
    assert all(
        pd.isna(group.iloc[0]["price_momentum_1d"])
        for _, group in frame.groupby("ticker", sort=True)
    )
    assert frame.loc[frame["ticker"] == "2317", "price_momentum_1d"].notna().sum() == 11
    assert frame.loc[frame["ticker"] == "2330", "price_momentum_1d"].notna().sum() == 11
