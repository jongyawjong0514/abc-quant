import pandas as pd

from abc_quant.data.local_tw_loader import DataQualityReport, LocalTwDataBundle
from abc_quant.features.walkline_features import (
    compute_walkline_features,
    forbidden_signal_feature_columns,
)
from abc_quant.signals.zhu_walkline_shadow import build_zhu_walkline_shadow_result


def _price_with_future(future_close: float) -> pd.DataFrame:
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, future_close]
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-07-04", periods=6, freq="D"),
            "stock_id": ["6830"] * 6,
            "open": closes,
            "high": [close + 1.0 for close in closes],
            "low": [close - 1.0 for close in closes],
            "close": closes,
            "volume": [1000, 1100, 1200, 1300, 1400, 999999],
        }
    )


def test_asof_filter_ignores_future_price_rows() -> None:
    base = compute_walkline_features(_price_with_future(15.0), asof_date="2026-07-08")
    mutated = compute_walkline_features(_price_with_future(999.0), asof_date="2026-07-08")

    columns = [
        "close",
        "ma5",
        "return_1d",
        "vol_ratio_5",
        "support_1",
        "resistance_1",
        "support_zone_1_low",
        "support_zone_1_high",
        "support_zone_1_label",
        "resistance_zone_1_low",
        "resistance_zone_1_high",
        "resistance_zone_1_label",
        "support_zone_failed_today",
        "resistance_zone_breakout_today",
    ]
    pd.testing.assert_frame_equal(base[columns], mutated[columns])


def test_forbidden_signal_feature_columns_detect_labels_and_forward_returns() -> None:
    forbidden = forbidden_signal_feature_columns(
        ["close", "future_return_d1", "label_d5", "rise_score"]
    )

    assert forbidden == ["future_return_d1", "label_d5"]


def test_signal_feature_matrix_excludes_forward_return_columns() -> None:
    result = _signal_result(99.0)

    assert forbidden_signal_feature_columns(result.feature_matrix.columns) == []
    assert "future_return_d1" not in result.feature_matrix.columns
    assert "label_d1" not in result.feature_matrix.columns


def test_signal_observation_fields_ignore_future_price_rows() -> None:
    base = _signal_result(15.0).feature_matrix
    mutated = _signal_result(999.0).feature_matrix

    columns = [
        "buy_observation_type",
        "buy_trigger_price",
        "target_resistance_1",
        "target_resistance_2",
        "sell_warning_type",
        "invalidation_price",
        "signal_stage",
        "trigger_type",
        "failure_type",
    ]
    pd.testing.assert_frame_equal(base[columns], mutated[columns])


def _signal_result(future_close: float):
    quality = DataQualityReport(sqlite_path="mock.sqlite", sqlite_exists=True)
    bundle = LocalTwDataBundle(
        asof_date="2026-07-08",
        requested_asof="2026-07-08",
        price_history=_price_with_future(future_close),
        stock_info=pd.DataFrame(
            {"stock_id": ["6830"], "stock_name": ["汎銓"], "sector": ["半導體設備"], "market": ["TWSE"]}
        ),
        chip_history=pd.DataFrame(),
        margin_history=pd.DataFrame(),
        holder_latest=pd.DataFrame(),
        market_history=pd.DataFrame(),
        sector_sentiment=pd.DataFrame(),
        stock_context=pd.DataFrame(),
        class_membership=pd.DataFrame(),
        data_quality=quality,
    )
    return build_zhu_walkline_shadow_result(
        bundle,
        concept_map={"SEMICONDUCTOR_EQUIPMENT": ["6830"]},
        web_records=[],
        top_n=5,
        web_research_used=False,
        config={"scoring": {"web_score_cap": 5}},
    )
