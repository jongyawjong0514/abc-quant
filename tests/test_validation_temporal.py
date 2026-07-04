import pandas as pd
import pytest

from abc_quant.validation.temporal import TemporalSplit, build_temporal_split


def _metadata() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker in ("2317", "2330"):
        for date in pd.date_range("2026-01-01", periods=6, freq="D"):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "label_forward_return": pd.NA
                    if date == pd.Timestamp("2026-01-06")
                    else 0.01,
                }
            )
    return pd.DataFrame(rows)


def _sorted_metadata(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.copy().sort_values(["date", "ticker"]).reset_index(drop=True)


def test_build_temporal_split_supports_train_test_contract() -> None:
    metadata = _metadata()

    split = build_temporal_split(metadata, train_end="2026-01-03")
    sorted_metadata = _sorted_metadata(metadata)

    assert isinstance(split, TemporalSplit)
    assert split.validation_index == ()
    assert split.train_index == tuple(range(6))
    assert split.test_index == tuple(range(6, 12))
    assert split.train_end == pd.Timestamp("2026-01-03")
    assert split.validation_end is None
    assert split.test_end is None

    train_dates = sorted_metadata.loc[list(split.train_index), "date"]
    test_dates = sorted_metadata.loc[list(split.test_index), "date"]
    assert train_dates.max() < test_dates.min()


def test_build_temporal_split_supports_train_validation_test_contract() -> None:
    metadata = _metadata()

    split = build_temporal_split(
        metadata,
        train_end="2026-01-02",
        validation_end="2026-01-04",
    )
    sorted_metadata = _sorted_metadata(metadata)

    assert split.train_index == tuple(range(4))
    assert split.validation_index == tuple(range(4, 8))
    assert split.test_index == tuple(range(8, 12))
    assert split.validation_end == pd.Timestamp("2026-01-04")
    assert split.validation_start_date == pd.Timestamp("2026-01-03")
    assert split.validation_end_date == pd.Timestamp("2026-01-04")

    train_dates = sorted_metadata.loc[list(split.train_index), "date"]
    validation_dates = sorted_metadata.loc[list(split.validation_index), "date"]
    test_dates = sorted_metadata.loc[list(split.test_index), "date"]
    assert train_dates.max() < validation_dates.min()
    assert validation_dates.max() < test_dates.min()
    assert set(split.train_index).isdisjoint(split.validation_index)
    assert set(split.train_index).isdisjoint(split.test_index)
    assert set(split.validation_index).isdisjoint(split.test_index)


def test_shuffled_metadata_produces_identical_sorted_index_membership() -> None:
    metadata = _metadata()
    shuffled = metadata.sample(frac=1.0, random_state=12).reset_index(drop=True)

    expected = build_temporal_split(
        metadata,
        train_end="2026-01-02",
        validation_end="2026-01-04",
    )
    actual = build_temporal_split(
        shuffled,
        train_end="2026-01-02",
        validation_end="2026-01-04",
    )

    assert actual == expected


def test_missing_labels_are_not_dropped_or_filled_by_split_contract() -> None:
    metadata = _metadata()

    split = build_temporal_split(metadata, train_end="2026-01-03")
    sorted_metadata = _sorted_metadata(metadata)

    assert len(split.train_index) + len(split.test_index) == len(sorted_metadata)
    assert sorted_metadata["label_forward_return"].isna().sum() == 2


def test_temporal_split_rejects_missing_or_unsortable_dates() -> None:
    with pytest.raises(ValueError, match="missing required date column"):
        build_temporal_split(pd.DataFrame({"ticker": ["2330"]}), train_end="2026-01-01")

    with pytest.raises(ValueError, match="date column is not sortable"):
        build_temporal_split(
            pd.DataFrame({"date": ["2026-01-01", "not-a-date"], "ticker": ["2330", "2330"]}),
            train_end="2026-01-01",
        )


def test_temporal_split_rejects_non_increasing_boundaries() -> None:
    metadata = _metadata()

    with pytest.raises(ValueError, match="boundaries must be increasing"):
        build_temporal_split(
            metadata,
            train_end="2026-01-03",
            validation_end="2026-01-03",
        )
    with pytest.raises(ValueError, match="boundaries must be increasing"):
        build_temporal_split(
            metadata,
            train_end="2026-01-03",
            test_end="2026-01-03",
        )
    with pytest.raises(ValueError, match="boundaries must be increasing"):
        build_temporal_split(
            metadata,
            train_end="2026-01-02",
            validation_end="2026-01-04",
            test_end="2026-01-04",
        )


def test_temporal_split_rejects_empty_splits() -> None:
    metadata = _metadata()

    with pytest.raises(ValueError, match="empty train split"):
        build_temporal_split(metadata, train_end="2025-12-31")
    with pytest.raises(ValueError, match="empty validation split"):
        build_temporal_split(
            metadata,
            train_end="2026-01-02",
            validation_end="2026-01-02 12:00:00",
        )
    with pytest.raises(ValueError, match="empty test split"):
        build_temporal_split(metadata, train_end="2026-01-06")


def test_temporal_split_rejects_rows_after_test_end_instead_of_dropping_them() -> None:
    with pytest.raises(ValueError, match="outside configured boundaries"):
        build_temporal_split(
            _metadata(),
            train_end="2026-01-02",
            validation_end="2026-01-04",
            test_end="2026-01-05",
        )
