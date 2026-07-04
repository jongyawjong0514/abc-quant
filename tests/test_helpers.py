from collections.abc import Sequence

import pandas as pd


def _assert_same_by_date_ticker(
    left: pd.DataFrame,
    right: pd.DataFrame,
    value_columns: Sequence[str],
) -> None:
    columns = ["date", "ticker", *value_columns]
    left_sorted = left.loc[:, columns].sort_values(["date", "ticker"]).reset_index(drop=True)
    right_sorted = right.loc[:, columns].sort_values(["date", "ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(left_sorted, right_sorted)


def _assert_same_feature_matrix(left: object, right: object) -> None:
    assert getattr(left, "feature_columns") == getattr(right, "feature_columns")
    assert getattr(left, "label_column") == getattr(right, "label_column")
    pd.testing.assert_frame_equal(getattr(left, "X"), getattr(right, "X"))
    pd.testing.assert_series_equal(getattr(left, "y"), getattr(right, "y"))
    pd.testing.assert_frame_equal(getattr(left, "metadata"), getattr(right, "metadata"))
