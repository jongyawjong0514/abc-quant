import pandas as pd
import pytest

from abc_quant.data.local_tw_loader import DataQualityReport, LocalTwDataBundle
from abc_quant.features.walkline_features import compute_walkline_features
from abc_quant.signals.zhu_walkline_shadow import build_zhu_walkline_shadow_result


def _mock_price_frame(stock_id: str = "2330", bearish: bool = False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2026-06-01", periods=30, freq="D")
    for index, dt in enumerate(dates):
        close = 50.0 + index if not bearish else 80.0 - index
        open_ = close - 1.0 if not bearish else close + 1.0
        if index == len(dates) - 1 and not bearish:
            open_ = close - 4.0
            close = close + 3.0
        if index == len(dates) - 1 and bearish:
            open_ = close + 4.0
            close = close - 3.0
        rows.append(
            {
                "date": dt,
                "stock_id": stock_id,
                "open": open_,
                "high": max(open_, close) + 1.0,
                "low": min(open_, close) - 1.0,
                "close": close,
                "volume": 1000.0 + index * 10,
            }
        )
    return pd.DataFrame(rows)


def test_walkline_features_compute_core_fields() -> None:
    features = compute_walkline_features(_mock_price_frame(), asof_date="2026-06-30")
    row = features.iloc[0]

    assert row["ma5"] == pytest.approx((75.0 + 76.0 + 77.0 + 78.0 + 82.0) / 5.0)
    assert row["ma10"] > row["ma20"]
    assert bool(row["ma_bull_alignment"])
    assert bool(row["close_above_prev_high"])
    assert bool(row["long_red_k"])
    assert row["upper_shadow_pct"] == pytest.approx(1.0 / 82.0)
    assert row["lower_shadow_pct"] == pytest.approx(1.0 / 82.0)
    assert row["vol_ratio_5"] > 0
    assert row["support_1"] <= row["close"]
    assert row["resistance_1"] >= row["close"]
    assert 0 <= row["risk_reward_proxy"] or pd.isna(row["risk_reward_proxy"])


def test_walkline_features_detect_bearish_alignment() -> None:
    features = compute_walkline_features(_mock_price_frame("2317", bearish=True), asof_date="2026-06-30")
    row = features.iloc[0]

    assert bool(row["ma_bear_alignment"])
    assert row["ma_state"] in {"BEAR_ALIGNMENT", "MA_BREAK"}
    assert row["kline_state"] in {"LONG_BLACK_K", "BREAKDOWN_K", "UPPER_SHADOW_SUPPLY"}


def test_zhu_walkline_scores_stay_bounded() -> None:
    price = pd.concat([_mock_price_frame("2330"), _mock_price_frame("2317", bearish=True)])
    quality = DataQualityReport(sqlite_path="mock.sqlite", sqlite_exists=True)
    bundle = LocalTwDataBundle(
        asof_date="2026-06-30",
        requested_asof="2026-06-30",
        price_history=price,
        stock_info=pd.DataFrame(
            {
                "stock_id": ["2330", "2317"],
                "stock_name": ["台積電", "鴻海"],
                "sector": ["半導體", "電子零組件"],
                "market": ["TWSE", "TWSE"],
            }
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
    result = build_zhu_walkline_shadow_result(
        bundle,
        concept_map={"SEMICONDUCTOR": ["2330"]},
        web_records=[],
        top_n=10,
        web_research_used=False,
        config={"scoring": {"web_score_cap": 5}},
    )

    assert result.feature_matrix["rise_score"].between(0, 100).all()
    assert result.feature_matrix["fall_risk_score"].between(0, 100).all()
    assert result.mode == "shadow_advisory_only"
    assert result.formal_champion_changed is False
    assert result.formal_trade_effect is False
