import pandas as pd
import pytest

from abc_quant.features.technical import add_technical_indicators
from test_helpers import _assert_same_by_date_ticker


TECHNICAL_COLUMNS = [
    "sma_3d",
    "ema_3d",
    "rsi_3d",
]


def _single_ticker_frame(close_tail: float = 15.0) -> pd.DataFrame:
    closes = [10.0, 11.0, 13.0, 12.0, close_tail]
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "ticker": ["2330"] * 5,
            "open": closes,
            "high": [close + 1.0 for close in closes],
            "low": [close - 1.0 for close in closes],
            "close": closes,
            "volume": [1000, 1100, 1200, 1300, 1400],
        }
    )


def _multi_ticker_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    specs = {
        "2317": [50.0, 52.0, 54.0, 56.0],
        "2330": [100.0, 90.0, 80.0, 70.0],
    }
    for ticker, closes in specs.items():
        for index, date in enumerate(pd.date_range("2026-01-01", periods=4, freq="D")):
            close = closes[index]
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": close,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1000 + index,
                }
            )
    return pd.DataFrame(rows)


def test_technical_indicators_match_hand_calculated_values() -> None:
    featured = add_technical_indicators(
        _single_ticker_frame(),
        sma_windows=(3,),
        ema_spans=(3,),
        rsi_windows=(3,),
    )

    assert featured.loc[2, "sma_3d"] == pytest.approx((10.0 + 11.0 + 13.0) / 3.0)
    assert featured.loc[3, "ema_3d"] == pytest.approx(11.875)
    assert featured.loc[3, "rsi_3d"] == pytest.approx(75.0)


def test_technical_indicators_are_isolated_by_ticker() -> None:
    featured = add_technical_indicators(
        _multi_ticker_frame(),
        sma_windows=(3,),
        ema_spans=(3,),
        rsi_windows=(3,),
    )

    first_by_ticker = featured.groupby("ticker", sort=True).head(1)
    assert first_by_ticker["sma_3d"].isna().all()
    assert first_by_ticker["ema_3d"].isna().all()
    assert first_by_ticker["rsi_3d"].isna().all()

    ticker_2317 = featured[featured["ticker"] == "2317"].reset_index(drop=True)
    ticker_2330 = featured[featured["ticker"] == "2330"].reset_index(drop=True)
    assert ticker_2317.loc[2, "sma_3d"] == pytest.approx(52.0)
    assert ticker_2330.loc[2, "sma_3d"] == pytest.approx(90.0)
    assert ticker_2317.loc[3, "rsi_3d"] == pytest.approx(100.0)
    assert ticker_2330.loc[3, "rsi_3d"] == pytest.approx(0.0)


def test_shuffled_input_produces_same_sorted_technical_indicators() -> None:
    sorted_input = _multi_ticker_frame()
    shuffled_input = sorted_input.sample(frac=1.0, random_state=31).reset_index(drop=True)

    sorted_featured = add_technical_indicators(
        sorted_input,
        sma_windows=(3,),
        ema_spans=(3,),
        rsi_windows=(3,),
    )
    shuffled_featured = add_technical_indicators(
        shuffled_input,
        sma_windows=(3,),
        ema_spans=(3,),
        rsi_windows=(3,),
    )

    _assert_same_by_date_ticker(sorted_featured, shuffled_featured, TECHNICAL_COLUMNS)


def test_future_price_changes_do_not_change_prior_technical_indicators() -> None:
    base = add_technical_indicators(
        _single_ticker_frame(close_tail=15.0),
        sma_windows=(3,),
        ema_spans=(3,),
        rsi_windows=(3,),
    )
    mutated_future = add_technical_indicators(
        _single_ticker_frame(close_tail=999.0),
        sma_windows=(3,),
        ema_spans=(3,),
        rsi_windows=(3,),
    )

    assert base.loc[3, "sma_3d"] == mutated_future.loc[3, "sma_3d"]
    assert base.loc[3, "ema_3d"] == mutated_future.loc[3, "ema_3d"]
    assert base.loc[3, "rsi_3d"] == mutated_future.loc[3, "rsi_3d"]


def test_technical_indicator_window_inputs_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="sma_windows must not be empty"):
        add_technical_indicators(_single_ticker_frame(), sma_windows=())


def test_technical_indicator_window_inputs_must_be_positive() -> None:
    with pytest.raises(ValueError, match="ema_spans must contain positive integers"):
        add_technical_indicators(_single_ticker_frame(), ema_spans=(0,))

    with pytest.raises(ValueError, match="rsi_windows must contain positive integers"):
        add_technical_indicators(_single_ticker_frame(), rsi_windows=(-1,))
