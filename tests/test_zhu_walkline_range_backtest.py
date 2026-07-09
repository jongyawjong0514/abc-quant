from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import backtest_zhu_walkline_shadow_range as range_backtest


def test_monthly_metrics_separate_fall_downside_and_adverse_rally() -> None:
    evaluations = pd.DataFrame(
        [
            _evaluation_row("2026-01-02", "fall", -0.04, True),
            _evaluation_row("2026-01-03", "fall", 0.04, False),
            _evaluation_row("2026-01-04", "fall", pd.NA, pd.NA),
            _evaluation_row("2026-01-02", "rise", -0.04, False),
        ]
    )

    monthly = range_backtest._monthly_metrics(evaluations)
    fall = monthly[(monthly["month"] == "2026-01") & (monthly["side"] == "fall")].iloc[0]
    rise = monthly[(monthly["month"] == "2026-01") & (monthly["side"] == "rise")].iloc[0]

    assert fall["rows"] == 3
    assert fall["valid_d5_rows"] == 2
    assert fall["missing_d5_rows"] == 1
    assert fall["hit_d5"] == pytest.approx(0.5)
    assert fall["fall_tail_down_rate_d5"] == pytest.approx(0.5)
    assert fall["fall_adverse_rally_rate_d5"] == pytest.approx(0.5)
    assert rise["rise_tail_loss_rate_d5"] == pytest.approx(1.0)


def test_summary_payload_reports_weighting_completeness_monthly_and_excess() -> None:
    evaluations = pd.DataFrame(
        [
            _evaluation_row("2026-01-02", "rise", -0.04, False, stock_id="2330"),
            _evaluation_row("2026-01-03", "rise", pd.NA, pd.NA, stock_id="2317"),
            _evaluation_row("2026-01-02", "fall", -0.04, True, stock_id="2454"),
            _evaluation_row("2026-01-03", "fall", 0.04, False, stock_id="2303"),
        ]
    )
    fake_result = SimpleNamespace(
        asof_date="2026-01-03",
        mode="shadow_observation_only",
        formal_champion_changed=False,
        formal_trade_effect=False,
        market={"market_state": "MARKET_RANGE_BOUND", "source": "fixture"},
        feature_matrix=pd.DataFrame({"stock_id": ["2330", "2317", "2454", "2303"]}),
        top_bullish_watchlist=pd.DataFrame(index=[0, 1]),
        top_fall_risks=pd.DataFrame(index=[0, 1]),
    )
    daily = pd.DataFrame([range_backtest._daily_metrics(fake_result, evaluations)])
    baselines = pd.DataFrame(
        [
            _baseline_row("rise", "all_market", "d5", hit_rate=0.25, avg_return=0.01),
            _baseline_row("fall", "all_market", "d5", hit_rate=0.25, avg_return=0.01),
        ]
    )
    monthly = range_backtest._monthly_metrics(evaluations)

    summary = range_backtest._summary_payload(
        start_date="2026-01-01",
        end_date="2026-01-31",
        trading_dates=["2026-01-02", "2026-01-03"],
        daily=daily,
        evaluations=evaluations,
        baselines=baselines,
        monthly=monthly,
        top_n=30,
        future_calendar_days=25,
        max_future_date_used="2026-02-09",
        elapsed_seconds=1.23,
    )

    assert "daily_metric_means" not in summary
    assert "daily_equal_weighted_metrics" in summary
    assert "row_weighted_metrics" in summary
    assert "valid_row_count_by_horizon" in summary
    assert "baseline_metrics" in summary
    assert "excess_vs_baseline" in summary
    assert summary["valid_row_count_by_horizon"]["D5"] == {
        "valid_row_count": 3,
        "missing_row_count": 1,
    }
    assert summary["row_weighted_metrics"]["fall"]["D5"]["valid_row_count"] == 2
    assert summary["row_weighted_metrics"]["fall"]["tail_down_rate_d5"] == pytest.approx(0.5)
    assert summary["row_weighted_metrics"]["fall"]["adverse_rally_rate_d5"] == pytest.approx(0.5)
    assert summary["excess_vs_baseline"]["rise"]["all_market"]["D5"]["excess_hit_rate"] == pytest.approx(-0.25)
    assert summary["monthly_preview"]


def test_baseline_metrics_include_all_market_random_same_count_and_score_decile() -> None:
    universe_forward = pd.DataFrame(
        {
            "stock_id": [f"{index:04d}" for index in range(10)],
            "rise_score": list(range(10)),
            "fall_risk_score": list(reversed(range(10))),
            "future_return_d1": [0.01 * (index - 4) for index in range(10)],
            "future_return_d3": [0.01 * (index - 4) for index in range(10)],
            "future_return_d5": [0.01 * (index - 4) for index in range(10)],
        }
    )
    evaluation_frame = pd.DataFrame(
        {
            "candidate_side": ["rise", "rise"],
            "stock_id": ["0008", "0009"],
        }
    )
    result = SimpleNamespace(asof_date="2026-01-05", market={"market_state": "MARKET_RANGE_BOUND"})

    rows = range_backtest._baseline_metrics_for_day(
        result,
        evaluation_frame,
        universe_forward,
        random_seed=7,
    )
    frame = pd.DataFrame(rows)

    assert {"all_market", "random_same_count"}.issubset(set(frame["baseline_type"]))
    assert any(str(value).startswith("score_decile_") for value in frame["baseline_type"])
    random_rise = frame[(frame["side"] == "rise") & (frame["baseline_type"] == "random_same_count")].iloc[0]
    assert random_rise["candidate_count"] == 2
    assert random_rise["baseline_rows"] == 2


def _evaluation_row(
    asof_date: str,
    side: str,
    d5_return: object,
    d5_hit: object,
    *,
    stock_id: str = "2330",
) -> dict[str, object]:
    return {
        "asof_date": asof_date,
        "stock_id": stock_id,
        "candidate_side": side,
        "future_return_d1": d5_return,
        "future_return_d3": d5_return,
        "future_return_d5": d5_return,
        "future_return_d10": d5_return,
        "hit_d1": d5_hit,
        "hit_d3": d5_hit,
        "hit_d5": d5_hit,
        "hit_d10": d5_hit,
    }


def _baseline_row(
    side: str,
    baseline_type: str,
    suffix: str,
    *,
    hit_rate: float,
    avg_return: float,
) -> dict[str, object]:
    row: dict[str, object] = {
        "asof_date": "2026-01-02",
        "market_state": "MARKET_RANGE_BOUND",
        "side": side,
        "baseline_type": baseline_type,
        "candidate_count": 2,
        "baseline_rows": 4,
    }
    for horizon in ("d1", "d3", "d5"):
        row[f"valid_rows_{horizon}"] = 4 if horizon == suffix else 0
        row[f"missing_rows_{horizon}"] = 0
        row[f"hit_rate_{horizon}"] = hit_rate if horizon == suffix else pd.NA
        row[f"avg_forward_return_{horizon}"] = avg_return if horizon == suffix else pd.NA
        row[f"median_forward_return_{horizon}"] = avg_return if horizon == suffix else pd.NA
    return row
