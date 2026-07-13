import pandas as pd

from abc_quant.data.local_tw_loader import DataQualityReport, LocalTwDataBundle
from abc_quant.features.walkline_features import (
    compute_walkline_features,
    forbidden_signal_feature_columns,
)
from abc_quant.signals.zhu_walkline_shadow import build_zhu_walkline_shadow_result


OBSERVATION_COLUMNS = [
    "buy_observation_type",
    "buy_observation_detail_types",
    "buy_trigger_price",
    "buy_trigger_price_role",
    "target_resistance_1",
    "target_resistance_2",
    "sell_warning_type",
    "sell_warning_detail_types",
    "invalidation_price",
    "signal_stage",
    "trigger_type",
    "failure_type",
    "kd_k9",
    "kd_d9",
    "kd_oversold_marker",
    "kd_recent_oversold",
    "kd_k_rising",
    "kd_above_d",
    "kd_bull_cross",
    "kd_recent_bull_cross",
    "kd_price_reclaim",
    "bull_trend_gate",
    "strong_stock_gate",
    "kd_recovery_confirmation",
    "kd_observation_stage",
    "kd_observation_type",
    "kd_reclaim_price",
    "support_1",
    "resistance_1",
    "support_zone_1_low",
    "support_zone_1_high",
    "resistance_zone_1_low",
    "resistance_zone_1_high",
    "stop_reference",
]


def _price_with_future(
    future_close: float,
    *,
    stock_id: str = "6830",
    future_high: float | None = None,
    future_low: float | None = None,
    future_volume: float = 999999,
) -> pd.DataFrame:
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, future_close]
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2026-07-04", periods=6, freq="D"),
            "stock_id": [stock_id] * 6,
            "open": closes,
            "high": [close + 1.0 for close in closes],
            "low": [close - 1.0 for close in closes],
            "close": closes,
            "volume": [1000, 1100, 1200, 1300, 1400, future_volume],
        }
    )
    if future_high is not None:
        frame.loc[len(frame) - 1, "high"] = future_high
    if future_low is not None:
        frame.loc[len(frame) - 1, "low"] = future_low
    return frame


def test_asof_filter_ignores_future_price_rows() -> None:
    base = compute_walkline_features(_price_with_future(15.0), asof_date="2026-07-08")
    mutated = compute_walkline_features(_price_with_future(999.0), asof_date="2026-07-08")

    columns = [
        "close",
        "ma5",
        "return_1d",
        "vol_ratio_5",
        "kd_k9",
        "kd_d9",
        "kd_oversold_marker",
        "kd_recent_oversold",
        "kd_k_rising",
        "kd_above_d",
        "kd_bull_cross",
        "kd_recent_bull_cross",
        "kd_price_reclaim",
        "bull_trend_gate",
        "strong_stock_gate",
        "kd_recovery_confirmation",
        "kd_observation_stage",
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

    pd.testing.assert_frame_equal(base[OBSERVATION_COLUMNS], mutated[OBSERVATION_COLUMNS])


def test_multi_stock_future_price_rows_do_not_change_observation_fields() -> None:
    base_price = pd.concat(
        [_price_with_future(15.0, stock_id="6830"), _price_with_future(25.0, stock_id="2464")],
        ignore_index=True,
    )
    mutated_price = pd.concat(
        [_price_with_future(999.0, stock_id="6830"), _price_with_future(1.0, stock_id="2464")],
        ignore_index=True,
    )
    base = _signal_result_from_price(base_price).feature_matrix.sort_values("stock_id").reset_index(drop=True)
    mutated = _signal_result_from_price(mutated_price).feature_matrix.sort_values("stock_id").reset_index(drop=True)

    pd.testing.assert_frame_equal(base[OBSERVATION_COLUMNS], mutated[OBSERVATION_COLUMNS])


def test_future_high_low_volume_do_not_change_support_resistance_or_observation() -> None:
    base = _signal_result_from_price(_price_with_future(15.0)).feature_matrix
    mutated = _signal_result_from_price(
        _price_with_future(
            15.0,
            future_high=9999.0,
            future_low=0.01,
            future_volume=999999999,
        )
    ).feature_matrix

    pd.testing.assert_frame_equal(base[OBSERVATION_COLUMNS], mutated[OBSERVATION_COLUMNS])


def test_future_chip_margin_holder_rows_do_not_change_observation_fields() -> None:
    base = _signal_result_with_context(
        future_chip_value=100,
        future_margin_balance=1000,
        future_holder_ratio=10.0,
    ).feature_matrix
    mutated = _signal_result_with_context(
        future_chip_value=999999999,
        future_margin_balance=999999999,
        future_holder_ratio=99.0,
    ).feature_matrix

    pd.testing.assert_frame_equal(base[OBSERVATION_COLUMNS], mutated[OBSERVATION_COLUMNS])


def test_resistance_turn_support_does_not_use_future_breakout_or_retest() -> None:
    base_price = _price_with_future(14.5)
    mutated_price = _price_with_future(14.5, future_high=40.0, future_low=13.8, future_volume=999999999)
    mutated_price.loc[len(mutated_price) - 1, "close"] = 30.0
    base = _signal_result_from_price(base_price).feature_matrix
    mutated = _signal_result_from_price(mutated_price).feature_matrix

    pd.testing.assert_frame_equal(base[OBSERVATION_COLUMNS], mutated[OBSERVATION_COLUMNS])
    assert "RESISTANCE_TURN_SUPPORT" not in str(base.loc[0, "buy_observation_detail_types"])


def _signal_result(future_close: float):
    return _signal_result_from_price(_price_with_future(future_close))


def _signal_result_from_price(
    price_history: pd.DataFrame,
    *,
    chip_history: pd.DataFrame | None = None,
    margin_history: pd.DataFrame | None = None,
    holder_latest: pd.DataFrame | None = None,
):
    quality = DataQualityReport(sqlite_path="mock.sqlite", sqlite_exists=True)
    bundle = LocalTwDataBundle(
        asof_date="2026-07-08",
        requested_asof="2026-07-08",
        price_history=price_history,
        stock_info=pd.DataFrame(
            {
                "stock_id": sorted(price_history["stock_id"].astype(str).unique()),
                "stock_name": ["汎銓"] * len(price_history["stock_id"].astype(str).unique()),
                "sector": ["半導體設備"] * len(price_history["stock_id"].astype(str).unique()),
                "market": ["TWSE"] * len(price_history["stock_id"].astype(str).unique()),
            }
        ),
        chip_history=chip_history if chip_history is not None else pd.DataFrame(),
        margin_history=margin_history if margin_history is not None else pd.DataFrame(),
        holder_latest=holder_latest if holder_latest is not None else pd.DataFrame(),
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


def _signal_result_with_context(
    *,
    future_chip_value: float,
    future_margin_balance: float,
    future_holder_ratio: float,
):
    chip_history = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-07-08", "2026-07-09"]),
            "stock_id": ["6830", "6830"],
            "foreign_net_buy_shares": [100.0, future_chip_value],
            "trust_net_buy_shares": [0.0, future_chip_value],
            "dealer_net_buy_shares": [0.0, future_chip_value],
            "dealer_hedge_net_buy_shares": [0.0, future_chip_value],
            "institutional_net_buy_shares": [100.0, future_chip_value],
        }
    )
    margin_history = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-07-08", "2026-07-09"]),
            "stock_id": ["6830", "6830"],
            "margin_balance": [1000.0, future_margin_balance],
        }
    )
    holder_latest = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-08", "2026-07-09"]),
            "stock_id": ["6830", "6830"],
            "big_holder_ratio_1000_lots_pct": [10.0, future_holder_ratio],
            "big_holder_ratio_1000_lots_pct_ma20": [9.0, 1.0],
        }
    )
    return _signal_result_from_price(
        _price_with_future(15.0),
        chip_history=chip_history,
        margin_history=margin_history,
        holder_latest=holder_latest,
    )
