import json

from abc_quant.data.web_cache import WebSourceCache, write_web_sources_jsonl
from abc_quant.features.news_event_features import compute_news_event_features


def test_web_event_scores_respect_asof_source_and_caps() -> None:
    records = [
        {
            "stock_id": "2330",
            "published_at": "2026-07-08",
            "source_priority": "official",
            "published_at_unknown": False,
            "event_sentiment_score": 1.0,
            "confidence": "high",
        },
        {
            "stock_id": "2317",
            "published_at": "2026-07-08",
            "source_priority": "reliable_media",
            "published_at_unknown": False,
            "event_sentiment_score": 1.0,
            "confidence": "medium",
        },
        {
            "stock_id": "2454",
            "published_at": "2026-07-08",
            "source_priority": "community",
            "published_at_unknown": False,
            "event_sentiment_score": 1.0,
            "confidence": "low",
        },
        {
            "stock_id": "3008",
            "published_at": "2026-07-09",
            "source_priority": "official",
            "published_at_unknown": False,
            "event_sentiment_score": 1.0,
            "confidence": "high",
        },
        {
            "stock_id": "1101",
            "published_at": "",
            "source_priority": "official",
            "published_at_unknown": True,
            "event_sentiment_score": 1.0,
            "confidence": "medium",
        },
        {
            "stock_id": "2002",
            "published_at": "2026-07-08",
            "source_priority": "official",
            "published_at_unknown": False,
            "event_sentiment_score": -1.0,
            "confidence": "high",
        },
    ]

    scored = compute_news_event_features(records, asof_date="2026-07-08", web_score_cap=5)
    by_stock = scored.set_index("stock_id")

    assert by_stock.loc["2330", "event_score_for_rise"] == 5.0
    assert by_stock.loc["2317", "event_score_for_rise"] == 3.0
    assert by_stock.loc["2454", "event_score_for_rise"] == 0.0
    assert by_stock.loc["3008", "event_score_for_rise"] == 0.0
    assert by_stock.loc["1101", "event_score_for_rise"] == 0.0
    assert by_stock.loc["2002", "event_score_for_fall"] == 5.0


def test_web_cache_writes_sqlite_and_jsonl(tmp_path) -> None:
    cache = WebSourceCache(tmp_path / "web_cache")
    records = [
        {
            "fetched_at": "2026-07-08 18:00:00",
            "asof_date": "2026-07-08",
            "stock_id": "2330",
            "stock_name": "台積電",
            "source_name": "MOPS",
            "url": "https://mops.twse.com.tw/",
            "title": "重大訊息",
            "published_at": "2026-07-08",
            "source_priority": "official",
            "content_summary": "summary",
            "used_in_score": True,
            "used_in_report": True,
            "confidence": "high",
            "published_at_unknown": False,
        }
    ]

    cache.append_records(records)
    loaded = cache.read_records(asof_date="2026-07-08", stock_id="2330")
    assert loaded[0]["stock_id"] == "2330"

    jsonl_path = tmp_path / "sources.jsonl"
    write_web_sources_jsonl(jsonl_path, records)
    line = jsonl_path.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["source_priority"] == "official"
    assert parsed["used_in_score"] is True
