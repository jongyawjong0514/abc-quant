from __future__ import annotations

from pathlib import Path

import pandas as pd

from abc_quant.data.yahoo_concepts import STATIC_CURRENT_BACKFILL
from abc_quant.features.yahoo_concept_rotation import (
    apply_hierarchical_context_gate,
    attach_best_yahoo_concept_context,
    compute_yahoo_concept_rotation,
    write_yahoo_concept_rotation,
)


def test_concept_rotation_is_asof_and_future_mutation_safe() -> None:
    membership = _membership()
    prices = _prices()

    base = compute_yahoo_concept_rotation(
        prices,
        membership,
        snapshot_date="2026-07-09",
        allow_static_current_backfill=True,
        min_available_members=3,
    )
    mutated_prices = prices.copy()
    mutated_prices.loc[mutated_prices["date"].eq("2026-06-08"), ["close", "sma20"]] = [1.0, 999.0]
    mutated = compute_yahoo_concept_rotation(
        mutated_prices,
        membership,
        snapshot_date="2026-07-09",
        allow_static_current_backfill=True,
        min_available_members=3,
    )

    base_day = base[base["asof_date"].eq("2026-06-07")].reset_index(drop=True)
    mutated_day = mutated[mutated["asof_date"].eq("2026-06-07")].reset_index(drop=True)
    pd.testing.assert_frame_equal(base_day, mutated_day)
    assert base_day.iloc[0]["concept_state"] == "CONCEPT_LEADING"
    assert base_day.iloc[0]["membership_mode"] == STATIC_CURRENT_BACKFILL


def test_context_attachment_selects_strongest_same_day_concept() -> None:
    candidates = pd.DataFrame([_candidate("1001")])
    rotation = compute_yahoo_concept_rotation(
        _prices(),
        _membership(),
        snapshot_date="2026-07-09",
        allow_static_current_backfill=True,
        min_available_members=3,
    )

    attached = attach_best_yahoo_concept_context(
        candidates,
        membership=_membership(),
        rotation=rotation,
        snapshot_date="2026-07-09",
    )

    assert attached.iloc[0]["best_concept_name"] == "AI人工智慧"
    assert attached.iloc[0]["concept_state"] == "CONCEPT_LEADING"
    assert attached.iloc[0]["concept_membership_mode"] == STATIC_CURRENT_BACKFILL


def test_hierarchy_gate_stops_at_first_failed_layer() -> None:
    rows = [
        _candidate("1001", market_state="MARKET_DOWNTREND"),
        _candidate("1002", sector_state="SECTOR_WEAK"),
        _candidate("1003", concept_state="CONCEPT_UNMAPPED"),
        _candidate("1004", driver_score=10.0),
        _candidate("1005"),
    ]

    gated = apply_hierarchical_context_gate(pd.DataFrame(rows), min_driver_score=11)

    assert gated["hierarchy_gate_stage"].tolist() == [
        "MARKET_BLOCKED",
        "SECTOR_BLOCKED",
        "CONCEPT_UNMAPPED",
        "INDIVIDUAL_SCORE_BELOW_THRESHOLD",
        "HIERARCHY_CONFIRMED",
    ]
    assert gated["hierarchy_observation_pass"].tolist() == [False, False, False, False, True]


def test_rotation_rows_are_persisted_by_snapshot_and_date(tmp_path: Path) -> None:
    rotation = compute_yahoo_concept_rotation(
        _prices(),
        _membership(),
        snapshot_date="2026-07-09",
        allow_static_current_backfill=True,
        min_available_members=3,
    )
    sqlite_path = tmp_path / "concept.sqlite"

    write_yahoo_concept_rotation(rotation, sqlite_path=sqlite_path)
    write_yahoo_concept_rotation(rotation, sqlite_path=sqlite_path)

    import sqlite3

    with sqlite3.connect(sqlite_path) as connection:
        rows = connection.execute("select count(*) from yahoo_concept_rotation_daily").fetchone()[0]
    assert rows == len(rotation)


def _membership() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "snapshot_id": "fixture_snapshot",
                "concept_name": "AI人工智慧",
                "stock_id": stock_id,
            }
            for stock_id in ["1001", "1002", "1003", "1004", "1005"]
        ]
    )


def _prices() -> pd.DataFrame:
    records = []
    for stock_index, stock_id in enumerate(["1001", "1002", "1003", "1004", "1005"]):
        for day in range(1, 9):
            records.append(
                {
                    "date": f"2026-06-{day:02d}",
                    "stock_id": stock_id,
                    "close": 100.0 + stock_index + day,
                    "sma20": 90.0 + stock_index + day,
                }
            )
    return pd.DataFrame(records)


def _candidate(
    stock_id: str,
    *,
    market_state: str = "MARKET_RANGE_BOUND",
    sector_state: str = "SECTOR_ROTATING_IN",
    concept_state: str = "CONCEPT_LEADING",
    driver_score: float = 12.0,
) -> dict[str, object]:
    return {
        "asof_date": "2026-06-07",
        "stock_id": stock_id,
        "market_state": market_state,
        "sector_state": sector_state,
        "concept_state": concept_state,
        "driver_score": driver_score,
    }
