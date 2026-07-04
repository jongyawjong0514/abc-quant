import pandas as pd
import pytest

from abc_quant.features.price_volume import add_price_volume_features


FEATURE_COLUMNS = [
    "price_momentum_1d",
    "price_momentum_2d",
    "price_volatility_2d",
    "volume_average_2d",
]


def _single_ticker_frame(close_tail: float = 19.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "ticker": ["2330"] * 5,
            "open": [10.0, 11.0, 13.0, 17.0, close_tail],
            "high": [10.5, 11.5, 13.5, 17.5, close_tail + 0.5],
            "low": [9.5, 10.5, 12.5, 16.5, close_tail - 0.5],
            "close": [10.0, 11.0, 13.0, 17.0, close_tail],
            "volume": [100, 110, 120, 130, 140],
        }
    )


def _multi_ticker_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    specs = {
        "2317": {
            "close": [50.0, 55.0, 60.0, 66.0],
            "volume": [1000, 1100, 1200, 1300],
        },
        "2330": {
            "close": [100.0, 90.0, 81.0, 72.9],
            "volume": [2000, 2100, 2200, 2300],
        },
    }
    for ticker, values in specs.items():
        for index, date in enumerate(pd.date_range("2026-01-01", periods=4, freq="D")):
            close = values["close"][index]
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": close,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": values["volume"][index],
                }
            )
    return pd.DataFrame(rows)


def test_rolling_price_volume_features_use_past_and_current_rows_only() -> None:
    base = add_price_volume_features(
        _single_ticker_frame(close_tail=19.0),
        momentum_windows=(2,),
        volatility_windows=(2,),
        volume_windows=(3,),
    )
    mutated_future = add_price_volume_features(
        _single_ticker_frame(close_tail=999.0),
        momentum_windows=(2,),
        volatility_windows=(2,),
        volume_windows=(3,),
    )

    assert base.loc[2, "price_momentum_2d"] == 13.0 / 10.0 - 1.0
    assert base.loc[2, "volume_average_3d"] == 110.0
    assert base.loc[2, "price_momentum_2d"] == mutated_future.loc[2, "price_momentum_2d"]
    assert base.loc[2, "price_volatility_2d"] == mutated_future.loc[2, "price_volatility_2d"]
    assert base.loc[2, "volume_average_3d"] == mutated_future.loc[2, "volume_average_3d"]


def test_price_volume_features_are_isolated_by_ticker() -> None:
    featured = add_price_volume_features(
        _multi_ticker_frame(),
        momentum_windows=(1, 2),
        volatility_windows=(2,),
        volume_windows=(2,),
    )

    first_by_ticker = featured.groupby("ticker", sort=True).head(1)
    assert first_by_ticker["price_momentum_1d"].isna().all()
    assert first_by_ticker["price_volatility_2d"].isna().all()
    assert first_by_ticker["volume_average_2d"].isna().all()

    ticker_2317 = featured[featured["ticker"] == "2317"].reset_index(drop=True)
    ticker_2330 = featured[featured["ticker"] == "2330"].reset_index(drop=True)
    assert ticker_2317.loc[1, "price_momentum_1d"] == pytest.approx(55.0 / 50.0 - 1.0)
    assert ticker_2330.loc[1, "price_momentum_1d"] == pytest.approx(90.0 / 100.0 - 1.0)
    assert ticker_2317.loc[1, "volume_average_2d"] == pytest.approx((1000 + 1100) / 2)
    assert ticker_2330.loc[1, "volume_average_2d"] == pytest.approx((2000 + 2100) / 2)


def test_shuffled_input_produces_same_sorted_price_volume_features() -> None:
    sorted_input = _multi_ticker_frame()
    shuffled_input = sorted_input.sample(frac=1.0, random_state=17).reset_index(drop=True)

    sorted_featured = add_price_volume_features(
        sorted_input,
        momentum_windows=(1, 2),
        volatility_windows=(2,),
        volume_windows=(2,),
    )
    shuffled_featured = add_price_volume_features(
        shuffled_input,
        momentum_windows=(1, 2),
        volatility_windows=(2,),
        volume_windows=(2,),
    )

    pd.testing.assert_frame_equal(
        sorted_featured[["date", "ticker", *FEATURE_COLUMNS]],
        shuffled_featured[["date", "ticker", *FEATURE_COLUMNS]],
    )
