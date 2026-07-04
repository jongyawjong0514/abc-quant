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
