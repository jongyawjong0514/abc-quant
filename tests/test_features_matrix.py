import pandas as pd
import pytest

from abc_quant.features.matrix import FeatureMatrix, build_feature_matrix
from test_helpers import _assert_same_feature_matrix


LABEL_COLUMN = "label_forward_return_3d_entry_lag_1d"


def _feature_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    specs = {
        "2317": [50.0, 55.0, 60.0],
        "2330": [100.0, 90.0, 81.0],
    }
    for ticker, closes in specs.items():
        for index, date in enumerate(pd.date_range("2026-01-01", periods=3, freq="D")):
            close = closes[index]
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1000 + index,
                    "price_momentum_1d": close / closes[index - 1] - 1.0
                    if index > 0
                    else pd.NA,
                    "sma_2d": sum(closes[max(0, index - 1) : index + 1]) / min(index + 1, 2),
                    "custom_alpha": index + (0.1 if ticker == "2317" else 0.2),
                    LABEL_COLUMN: [0.10, 0.20, pd.NA][index],
                    "label_debug_target": [1.0, 2.0, pd.NA][index],
                }
            )
    return pd.DataFrame(rows)


def test_inferred_features_exclude_metadata_ohlcv_and_labels() -> None:
    matrix = build_feature_matrix(_feature_frame(), LABEL_COLUMN)

    assert isinstance(matrix, FeatureMatrix)
    assert matrix.feature_columns == ("price_momentum_1d", "sma_2d", "custom_alpha")
    assert list(matrix.X.columns) == list(matrix.feature_columns)
    assert matrix.label_column == LABEL_COLUMN
    assert list(matrix.metadata.columns) == ["date", "ticker"]
    assert len(matrix.X) == len(matrix.y) == len(matrix.metadata) == len(_feature_frame())


def test_explicit_feature_selection_preserves_order() -> None:
    matrix = build_feature_matrix(
        _feature_frame(),
        LABEL_COLUMN,
        feature_columns=["custom_alpha", "price_momentum_1d"],
    )

    assert matrix.feature_columns == ("custom_alpha", "price_momentum_1d")
    assert list(matrix.X.columns) == ["custom_alpha", "price_momentum_1d"]


def test_explicit_feature_selection_rejects_label_leakage_and_reserved_columns() -> None:
    frame = _feature_frame()

    with pytest.raises(ValueError, match="reserved or label"):
        build_feature_matrix(frame, LABEL_COLUMN, feature_columns=["custom_alpha", LABEL_COLUMN])
    with pytest.raises(ValueError, match="reserved or label"):
        build_feature_matrix(
            frame,
            LABEL_COLUMN,
            feature_columns=["custom_alpha", "label_debug_target"],
        )
    with pytest.raises(ValueError, match="reserved or label"):
        build_feature_matrix(frame, LABEL_COLUMN, feature_columns=["custom_alpha", "close"])
    with pytest.raises(ValueError, match="reserved or label"):
        build_feature_matrix(frame, LABEL_COLUMN, feature_columns=["custom_alpha", "ticker"])


def test_shuffled_input_produces_same_sorted_feature_matrix() -> None:
    sorted_input = _feature_frame()
    shuffled_input = sorted_input.sample(frac=1.0, random_state=41).reset_index(drop=True)

    sorted_matrix = build_feature_matrix(sorted_input, LABEL_COLUMN)
    shuffled_matrix = build_feature_matrix(shuffled_input, LABEL_COLUMN)

    _assert_same_feature_matrix(sorted_matrix, shuffled_matrix)


def test_missing_labels_are_preserved() -> None:
    matrix = build_feature_matrix(_feature_frame(), LABEL_COLUMN)

    assert matrix.y.isna().sum() == 2
    assert matrix.y.iloc[2:].isna().any()


def test_label_column_must_exist_and_cannot_be_a_feature() -> None:
    frame = _feature_frame()

    with pytest.raises(ValueError, match="missing required columns: missing_label"):
        build_feature_matrix(frame, "missing_label")
    with pytest.raises(ValueError, match="reserved or label"):
        build_feature_matrix(
            frame,
            LABEL_COLUMN,
            feature_columns=["price_momentum_1d", LABEL_COLUMN],
        )


def test_no_safe_inferred_feature_columns_raise() -> None:
    frame = _feature_frame().loc[
        :,
        ["date", "ticker", "open", "high", "low", "close", "volume", LABEL_COLUMN],
    ]

    with pytest.raises(ValueError, match="no feature columns remain"):
        build_feature_matrix(frame, LABEL_COLUMN)
