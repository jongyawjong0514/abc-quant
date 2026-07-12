from __future__ import annotations

from pathlib import Path

import pandas as pd

from abc_quant.data.yahoo_concepts import (
    IMPORTANT_BASELINE,
    POINT_IN_TIME_SNAPSHOT,
    STATIC_CURRENT_BACKFILL,
    YahooConceptSnapshot,
    build_class_quotes_api_url,
    load_important_yahoo_concept_snapshot,
    membership_mode_for_date,
    parse_class_quotes_payload,
    parse_concept_categories,
    write_yahoo_concept_snapshot,
)


def test_parse_concept_categories_keeps_only_concept_layer_and_deduplicates() -> None:
    page = """
    <a href="/class-quote?category=AI%E4%BA%BA%E5%B7%A5%E6%99%BA%E6%85%A7&amp;categoryLabel=%E6%A6%82%E5%BF%B5%E8%82%A1">AI人工智慧</a>
    <a href="/class-quote?category=AI%E4%BA%BA%E5%B7%A5%E6%99%BA%E6%85%A7&amp;categoryLabel=%E6%A6%82%E5%BF%B5%E8%82%A1">duplicate</a>
    <a href="/class-quote?category=%E5%8D%8A%E5%B0%8E%E9%AB%94&amp;categoryLabel=%E4%B8%8A%E5%B8%82%E9%A1%9E%E8%82%A1">半導體</a>
    """

    categories = parse_concept_categories(page)

    assert [category.concept_name for category in categories] == ["AI人工智慧"]
    assert "categoryLabel=%E6%A6%82%E5%BF%B5%E8%82%A1" in categories[0].source_url


def test_class_quotes_api_url_contains_offset_and_encoded_concept() -> None:
    url = build_class_quotes_api_url("機器人/智慧機械", offset=30)

    assert "category=%E6%A9%9F%E5%99%A8%E4%BA%BA%2F%E6%99%BA%E6%85%A7%E6%A9%9F%E6%A2%B0" in url
    assert ";offset=30?" in url


def test_parse_class_quotes_payload_normalizes_stock_rows() -> None:
    payload = {
        "data": {
            "list": [
                {
                    "symbol": "5488.TWO",
                    "symbolName": "松普",
                    "holdingType": "EQUITY",
                    "tradeDate": "2026-07-09T00:00:00+08:00",
                },
                {"symbol": "NOT_A_STOCK", "symbolName": "ignore"},
            ],
            "pagination": {"resultsTotal": 1, "nextOffset": None},
        }
    }

    rows, pagination = parse_class_quotes_payload(
        payload,
        concept_name="fixture",
        source_url="https://example.test/fixture",
    )

    assert rows == [
        {
            "concept_name": "fixture",
            "stock_id": "5488",
            "yahoo_symbol": "5488.TWO",
            "stock_name": "松普",
            "market_suffix": "TWO",
            "holding_type": "EQUITY",
            "trade_date": "2026-07-09",
            "source_url": "https://example.test/fixture",
        }
    ]
    assert pagination["resultsTotal"] == 1


def test_snapshot_sqlite_round_trip_is_append_only(tmp_path: Path) -> None:
    snapshot = _snapshot()
    sqlite_path = tmp_path / "concepts.sqlite"

    assert write_yahoo_concept_snapshot(snapshot, sqlite_path=sqlite_path) is True
    assert write_yahoo_concept_snapshot(snapshot, sqlite_path=sqlite_path) is False
    manifest, membership = load_important_yahoo_concept_snapshot(sqlite_path)

    assert manifest["snapshot_id"] == "fixture_snapshot"
    assert manifest["is_important"] == 1
    assert manifest["fetched_at"] == "2026-07-12T12:00:00+08:00"
    assert membership[["concept_name", "stock_id"]].to_dict("records") == [
        {"concept_name": "AI人工智慧", "stock_id": "5488"}
    ]


def test_static_backfill_mode_is_explicit() -> None:
    assert (
        membership_mode_for_date(
            "2026-06-01",
            snapshot_date="2026-07-09",
            allow_static_current_backfill=True,
        )
        == STATIC_CURRENT_BACKFILL
    )
    assert (
        membership_mode_for_date(
            "2026-06-01",
            snapshot_date="2026-07-09",
            allow_static_current_backfill=False,
        )
        == "point_in_time_unavailable"
    )


def _snapshot() -> YahooConceptSnapshot:
    manifest = {
        "snapshot_id": "fixture_snapshot",
        "snapshot_date": "2026-07-09",
        "fetched_at": "2026-07-12T12:00:00+08:00",
        "source_url": "https://tw.stock.yahoo.com/class",
        "category_label": "概念股",
        "category_count": 1,
        "membership_count": 1,
        "unique_stock_count": 1,
        "content_sha256": "fixture_hash",
        "importance": IMPORTANT_BASELINE,
        "is_important": True,
        "membership_mode": POINT_IN_TIME_SNAPSHOT,
        "static_backfill_authorized": True,
        "status": "complete",
    }
    categories = pd.DataFrame(
        [
            {
                "snapshot_id": "fixture_snapshot",
                "concept_name": "AI人工智慧",
                "source_url": "https://example.test/ai",
                "reported_count": 1,
                "downloaded_count": 1,
                "max_trade_date": "2026-07-09",
            }
        ]
    )
    membership = pd.DataFrame(
        [
            {
                "snapshot_id": "fixture_snapshot",
                "concept_name": "AI人工智慧",
                "stock_id": "5488",
                "yahoo_symbol": "5488.TWO",
                "stock_name": "松普",
                "market_suffix": "TWO",
                "holding_type": "EQUITY",
                "trade_date": "2026-07-09",
                "source_url": "https://example.test/ai",
            }
        ]
    )
    return YahooConceptSnapshot(manifest, categories, membership)
