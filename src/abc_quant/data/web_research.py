"""Supplemental official-event research from local web mirrors."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd

from abc_quant.data.web_cache import WebSourceCache


def collect_web_research(
    config: dict[str, Any],
    stock_info: pd.DataFrame,
    *,
    asof_date: str,
    max_results: int,
    cache: WebSourceCache,
) -> list[dict[str, Any]]:
    """Collect supplemental official major-news records from the local mirror.

    This function intentionally uses only locally mirrored official event tables.
    It does not scrape blocked sites, bypass paywalls, or replace local OHLCV and
    chip data.
    """
    sqlite_path = Path(config.get("data", {}).get("sqlite_path", ""))
    if not sqlite_path.exists() or stock_info.empty:
        return []
    stock_names = (
        stock_info[["stock_id", "stock_name"]]
        .dropna(subset=["stock_id"])
        .assign(stock_id=lambda frame: frame["stock_id"].astype(str))
        .drop_duplicates("stock_id")
        .set_index("stock_id")["stock_name"]
        .to_dict()
    )
    with sqlite3.connect(sqlite_path) as connection:
        records = _collect_twse_major_news(connection, stock_names, asof_date=asof_date)
        records.extend(_collect_tpex_major_news(connection, stock_names, asof_date=asof_date))
    records = _limit_per_stock(records, max_results=max_results)
    cache.append_records(records)
    return records


def _collect_twse_major_news(
    connection: sqlite3.Connection,
    stock_names: dict[str, str],
    *,
    asof_date: str,
) -> list[dict[str, Any]]:
    if not _table_exists(connection, "official_twse_major_news"):
        return []
    query = """
        select 公司代號 as stock_id,
               公司名稱 as stock_name,
               "發言日期" as publish_date,
               "主旨 " as title,
               "說明" as content_summary,
               "_source_url" as url
        from official_twse_major_news
    """
    frame = pd.read_sql_query(query, connection)
    return _records_from_major_news(
        frame,
        stock_names,
        source_name="TWSE major news",
        asof_date=asof_date,
    )


def _collect_tpex_major_news(
    connection: sqlite3.Connection,
    stock_names: dict[str, str],
    *,
    asof_date: str,
) -> list[dict[str, Any]]:
    if not _table_exists(connection, "official_tpex_major_news"):
        return []
    query = """
        select SecuritiesCompanyCode as stock_id,
               CompanyName as stock_name,
               發言日期 as publish_date,
               主旨 as title,
               說明 as content_summary,
               _source_url as url
        from official_tpex_major_news
    """
    frame = pd.read_sql_query(query, connection)
    return _records_from_major_news(
        frame,
        stock_names,
        source_name="TPEx major news",
        asof_date=asof_date,
    )


def _records_from_major_news(
    frame: pd.DataFrame,
    stock_names: dict[str, str],
    *,
    source_name: str,
    asof_date: str,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    cutoff = pd.to_datetime(asof_date)
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        stock_id = _normalize_stock_id(row.get("stock_id"))
        if stock_id not in stock_names:
            continue
        published_at = _normalize_tw_date(row.get("publish_date"))
        published_unknown = not bool(published_at)
        if published_at and pd.to_datetime(published_at) > cutoff:
            continue
        title = str(row.get("title", "") or "").strip()
        summary = str(row.get("content_summary", "") or "").strip()
        sentiment = _event_sentiment(title + " " + summary)
        rows.append(
            {
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "asof_date": asof_date,
                "stock_id": stock_id,
                "stock_name": str(row.get("stock_name") or stock_names.get(stock_id, "")),
                "source_name": source_name,
                "url": str(row.get("url", "") or ""),
                "title": title,
                "published_at": published_at,
                "source_priority": "official",
                "content_summary": summary[:500],
                "used_in_score": not published_unknown,
                "used_in_report": True,
                "confidence": "high" if not published_unknown else "medium",
                "published_at_unknown": published_unknown,
                "event_sentiment_score": sentiment,
            }
        )
    return rows


def _limit_per_stock(records: list[dict[str, Any]], *, max_results: int) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    limited: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item.get("published_at", ""), reverse=True):
        stock_id = str(record.get("stock_id", ""))
        if counts.get(stock_id, 0) >= max_results:
            continue
        counts[stock_id] = counts.get(stock_id, 0) + 1
        limited.append(record)
    return limited


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _normalize_tw_date(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 7:
        year = int(digits[:3]) + 1911
        return f"{year:04d}-{int(digits[3:5]):02d}-{int(digits[5:7]):02d}"
    if len(digits) == 8:
        return f"{int(digits[:4]):04d}-{int(digits[4:6]):02d}-{int(digits[6:8]):02d}"
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return ""
    return parsed.date().isoformat()


def _event_sentiment(text: str) -> float:
    negative_terms = ["處分", "警示", "違約", "重大損失", "停工", "下修", "衰退", "虧損"]
    positive_terms = ["成長", "創新高", "得標", "增資用途", "合作", "新產品", "營收增加"]
    if any(term in text for term in negative_terms):
        return -1.0
    if any(term in text for term in positive_terms):
        return 1.0
    return 0.0


def _normalize_stock_id(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:4] if len(digits) >= 4 else digits.zfill(4)
