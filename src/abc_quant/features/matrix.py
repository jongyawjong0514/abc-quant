"""Feature matrix assembly contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import pandas as pd

from abc_quant.data.schema import (
    CLOSE_COLUMN,
    DATE_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    OPEN_COLUMN,
    TICKER_COLUMN,
    VOLUME_COLUMN,
)

METADATA_COLUMNS: Final[tuple[str, ...]] = (DATE_COLUMN, TICKER_COLUMN)
RAW_OHLCV_COLUMNS: Final[tuple[str, ...]] = (
    OPEN_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    CLOSE_COLUMN,
    VOLUME_COLUMN,
)
LABEL_PREFIX: Final[str] = "label_"


@dataclass(frozen=True)
class FeatureMatrix:
    """Separated modeling inputs, evaluator target, and row metadata."""

    X: pd.DataFrame
    y: pd.Series
    metadata: pd.DataFrame
    feature_columns: tuple[str, ...]
    label_column: str


def build_feature_matrix(
    frame: pd.DataFrame,
    label_column: str,
    feature_columns: Sequence[str] | None = None,
) -> FeatureMatrix:
    """Build a deterministic feature matrix without label leakage.

    Rows are sorted by ``ticker`` then ``date``. The output preserves one row
    per input row, including missing labels, and does not scale, impute, fill,
    or split the data.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if not str(label_column).strip():
        raise ValueError("label_column must not be empty")

    label = str(label_column)
    _require_columns(frame, (*METADATA_COLUMNS, label))

    data = _normalized_sorted_copy(frame)
    selected_features = (
        _infer_feature_columns(data, label)
        if feature_columns is None
        else _validate_explicit_feature_columns(data, label, feature_columns)
    )
    if not selected_features:
        raise ValueError("no feature columns remain after applying exclusions")

    return FeatureMatrix(
        X=data.loc[:, selected_features].copy(),
        y=data.loc[:, label].copy(),
        metadata=data.loc[:, METADATA_COLUMNS].copy(),
        feature_columns=selected_features,
        label_column=label,
    )


def _normalized_sorted_copy(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    try:
        data[DATE_COLUMN] = pd.to_datetime(data[DATE_COLUMN], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("date column is not sortable") from exc

    if data[DATE_COLUMN].isna().any():
        raise ValueError("date column contains missing values")
    if data[TICKER_COLUMN].isna().any():
        raise ValueError("ticker column contains missing values")

    data[TICKER_COLUMN] = data[TICKER_COLUMN].astype("string")
    duplicate_mask = data.duplicated(subset=list(METADATA_COLUMNS), keep=False)
    if duplicate_mask.any():
        examples = data.loc[duplicate_mask, list(METADATA_COLUMNS)].head(5)
        raise ValueError(
            "feature matrix input contains duplicate date+ticker rows: "
            + examples.to_dict(orient="records").__repr__()
        )

    return data.sort_values(list(METADATA_COLUMNS)).reset_index(drop=True)


def _infer_feature_columns(frame: pd.DataFrame, label_column: str) -> tuple[str, ...]:
    return tuple(
        str(column)
        for column in frame.columns
        if not _is_reserved_feature_column(str(column), label_column)
    )


def _validate_explicit_feature_columns(
    frame: pd.DataFrame,
    label_column: str,
    feature_columns: Sequence[str],
) -> tuple[str, ...]:
    normalized = tuple(str(column) for column in feature_columns)
    if not normalized:
        raise ValueError("feature_columns must not be empty")

    duplicates = sorted({column for column in normalized if normalized.count(column) > 1})
    if duplicates:
        raise ValueError("feature_columns contains duplicates: " + ", ".join(duplicates))

    _require_columns(frame, normalized)
    reserved = [
        column for column in normalized if _is_reserved_feature_column(column, label_column)
    ]
    if reserved:
        raise ValueError(
            "feature_columns include reserved or label columns: " + ", ".join(reserved)
        )
    return normalized


def _is_reserved_feature_column(column: str, label_column: str) -> bool:
    return (
        column in METADATA_COLUMNS
        or column in RAW_OHLCV_COLUMNS
        or column == label_column
        or column.startswith(LABEL_PREFIX)
    )


def _require_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError("frame missing required columns: " + ", ".join(missing))
