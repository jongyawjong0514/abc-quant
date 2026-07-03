import pandas as pd

from abc_quant.features.price_volume import add_price_volume_features


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
