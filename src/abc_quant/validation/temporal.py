"""Temporal split contracts for leakage-safe modeling preparation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from abc_quant.data.schema import DATE_COLUMN, TICKER_COLUMN


@dataclass(frozen=True)
class TemporalSplit:
    """Deterministic positional indices and date boundaries for a time split."""

    train_index: tuple[int, ...]
    validation_index: tuple[int, ...]
    test_index: tuple[int, ...]
    date_column: str
    train_end: pd.Timestamp
    validation_end: pd.Timestamp | None
    test_end: pd.Timestamp | None
    train_start_date: pd.Timestamp
    train_end_date: pd.Timestamp
    validation_start_date: pd.Timestamp | None
    validation_end_date: pd.Timestamp | None
    test_start_date: pd.Timestamp
    test_end_date: pd.Timestamp


def build_temporal_split(
    metadata: pd.DataFrame,
    train_end: Any,
    validation_end: Any | None = None,
    test_end: Any | None = None,
    date_column: str = DATE_COLUMN,
) -> TemporalSplit:
    """Build deterministic train/test or train/validation/test split indices.

    The returned indices are positional indices for metadata sorted by
    ``date_column`` and then ``ticker`` when a ticker column is present. The
    function only validates split boundaries and never drops rows, fills labels,
    fits scalers, trains models, or creates strategy/backtest logic.
    """
    if not isinstance(metadata, pd.DataFrame):
        raise TypeError("metadata must be a pandas DataFrame")
    if not str(date_column).strip():
        raise ValueError("date_column must not be empty")
    if date_column not in metadata.columns:
        raise ValueError(f"metadata missing required date column: {date_column}")

    train_end_ts = _coerce_boundary(train_end, "train_end")
    validation_end_ts = (
        None
        if validation_end is None
        else _coerce_boundary(validation_end, "validation_end")
    )
    test_end_ts = None if test_end is None else _coerce_boundary(test_end, "test_end")
    _validate_boundaries(train_end_ts, validation_end_ts, test_end_ts)

    sorted_metadata = _normalized_sorted_metadata(metadata, date_column)
    dates = sorted_metadata[date_column]

    train_mask = dates <= train_end_ts
    if validation_end_ts is None:
        validation_mask = pd.Series(False, index=sorted_metadata.index)
        test_mask = dates > train_end_ts
    else:
        validation_mask = (dates > train_end_ts) & (dates <= validation_end_ts)
        test_mask = dates > validation_end_ts

    if test_end_ts is not None:
        test_mask &= dates <= test_end_ts

    assigned_mask = train_mask | validation_mask | test_mask
    if not assigned_mask.all():
        examples = sorted_metadata.loc[~assigned_mask, [date_column]].head(5)
        raise ValueError(
            "temporal split leaves rows outside configured boundaries: "
            + examples.to_dict(orient="records").__repr__()
        )

    train_index = _mask_to_positions(train_mask)
    validation_index = _mask_to_positions(validation_mask)
    test_index = _mask_to_positions(test_mask)

    if not train_index:
        raise ValueError("temporal split produced an empty train split")
    if validation_end_ts is not None and not validation_index:
        raise ValueError("temporal split produced an empty validation split")
    if not test_index:
        raise ValueError("temporal split produced an empty test split")

    return TemporalSplit(
        train_index=train_index,
        validation_index=validation_index,
        test_index=test_index,
        date_column=date_column,
        train_end=train_end_ts,
        validation_end=validation_end_ts,
        test_end=test_end_ts,
        train_start_date=_date_at_positions(dates, train_index, "min"),
        train_end_date=_date_at_positions(dates, train_index, "max"),
        validation_start_date=_optional_date_at_positions(dates, validation_index, "min"),
        validation_end_date=_optional_date_at_positions(dates, validation_index, "max"),
        test_start_date=_date_at_positions(dates, test_index, "min"),
        test_end_date=_date_at_positions(dates, test_index, "max"),
    )


def _coerce_boundary(value: Any, name: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not a sortable date") from exc
    if pd.isna(timestamp):
        raise ValueError(f"{name} must not be missing")
    return timestamp


def _validate_boundaries(
    train_end: pd.Timestamp,
    validation_end: pd.Timestamp | None,
    test_end: pd.Timestamp | None,
) -> None:
    if validation_end is not None and validation_end <= train_end:
        raise ValueError("temporal split boundaries must be increasing")
    if test_end is None:
        return
    previous_end = validation_end if validation_end is not None else train_end
    if test_end <= previous_end:
        raise ValueError("temporal split boundaries must be increasing")


def _normalized_sorted_metadata(
    metadata: pd.DataFrame,
    date_column: str,
) -> pd.DataFrame:
    data = metadata.copy()
    try:
        data[date_column] = pd.to_datetime(data[date_column], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{date_column} column is not sortable") from exc
    if data[date_column].isna().any():
        raise ValueError(f"{date_column} column contains missing values")

    sort_columns = [date_column]
    if TICKER_COLUMN in data.columns and TICKER_COLUMN != date_column:
        data[TICKER_COLUMN] = data[TICKER_COLUMN].astype("string")
        sort_columns.append(TICKER_COLUMN)

    return data.sort_values(sort_columns).reset_index(drop=True)


def _mask_to_positions(mask: pd.Series) -> tuple[int, ...]:
    return tuple(int(position) for position in mask[mask].index.to_list())


def _date_at_positions(
    dates: pd.Series,
    positions: tuple[int, ...],
    mode: str,
) -> pd.Timestamp:
    if not positions:
        raise ValueError("cannot compute date boundary for an empty split")
    values = dates.iloc[list(positions)]
    return values.min() if mode == "min" else values.max()


def _optional_date_at_positions(
    dates: pd.Series,
    positions: tuple[int, ...],
    mode: str,
) -> pd.Timestamp | None:
    if not positions:
        return None
    return _date_at_positions(dates, positions, mode)
